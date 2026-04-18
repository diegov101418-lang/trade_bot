"""
Recomendador de estrategias - Sugiere estrategia óptima y modo de riesgo
"""

from typing import Dict, Any, List, Optional
import logging
import time

import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from .core import BaseModel
from .encoders import FeatureEncoder

logger = logging.getLogger(__name__)


class StrategyRecommender(BaseModel):
    """
    Recomienda estrategia de trading y modo de riesgo basado en condiciones de mercado.

    Modos:
    - 'strategy': Recomienda nombre de estrategia
    - 'risk': Recomienda modo de riesgo
    """

    FEATURES = [
        "rsi",
        "volume",
        "trend",
        "momentum",
        "hour",
        "day_of_week",
        "signal_confidence",
        "atr",
        "market_regime_num",
        "volatility_context_num",
    ]

    def __init__(self, config: Optional[Any] = None, mode: str = "strategy"):
        self.mode = mode

        if mode not in ("strategy", "risk"):
            raise ValueError(f"Modo no válido: {mode}. Use 'strategy' o 'risk'")

        super().__init__(config)

    @property
    def model_file(self) -> str:
        if self.mode == "strategy":
            return "strategy_selector.pkl"
        return "risk_selector.pkl"

    @property
    def target_column(self) -> str:
        if self.mode == "strategy":
            return "strategy_name"
        return "risk_mode"

    @property
    def features(self) -> List[str]:
        return self.FEATURES
    
    @property
    def min_samples_required(self) -> int:
        return self.config.min_samples_strategy

    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Procesa features numéricas y categóricas.
        """
        df = df.copy()

        numeric_cols = [
            "rsi",
            "volume",
            "trend",
            "momentum",
            "hour",
            "day_of_week",
            "signal_confidence",
            "atr",
        ]

        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df["market_regime_num"] = df["market_regime"].apply(
            FeatureEncoder.market_regime
        )
        df["volatility_context_num"] = df["volatility_context"].apply(
            FeatureEncoder.volatility
        )

        return df

    def prepare_target(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepara la columna target según el modo.
        """
        df = df.copy()

        df[self.target_column] = df[self.target_column].astype(str)
        df = df[df[self.target_column].str.strip() != ""]

        # Preferencia por aprender desde trades netamente rentables
        if "result_net" in df.columns:
            df["result_net"] = pd.to_numeric(df["result_net"], errors="coerce")
            df_winners = df[df["result_net"] == 1]

            if len(df_winners) >= max(20, self.config.min_samples_strategy // 2):
                logger.info(
                    f"📈 Usando {len(df_winners)} trades netamente ganadores para entrenar {self.mode}"
                )
                df = df_winners

        # Compatibilidad hacia atrás si no existe result_net
        elif "result" in df.columns:
            df["result"] = pd.to_numeric(df["result"], errors="coerce")
            df_winners = df[df["result"] == 1]

            if len(df_winners) >= max(20, self.config.min_samples_strategy // 2):
                logger.info(
                    f"📈 Usando {len(df_winners)} trades ganadores para entrenar {self.mode}"
                )
                df = df_winners

        return df

    def _fit_model(self, df: pd.DataFrame) -> bool:
        """
        Entrena el clasificador de estrategia/riesgo.
        """
        X = df[self.features]
        y = df[self.target_column].astype(str)

        unique_classes = y.nunique()
        if unique_classes < 2:
            logger.warning(
                f"⚠ {self.mode}: Solo {unique_classes} clase(s) disponible(s): "
                f"{sorted(y.unique().tolist())}"
            )
            return False

        logger.info(
            f"📊 Entrenando {self.mode} selector con {len(df)} muestras, "
            f"{unique_classes} clases: {sorted(y.unique().tolist())}"
        )

        try:
            self.model = RandomForestClassifier(
                n_estimators=self.config.n_estimators,
                max_depth=self.config.max_depth,
                min_samples_leaf=self.config.min_samples_leaf,
                random_state=self.config.random_state,
                n_jobs=-1,
            )

            # Dar más peso a trades ganadores sin ignorar los perdedores
            if "result_net" in df.columns:
                df["result_net"] = pd.to_numeric(df["result_net"], errors="coerce")
                sample_weight = df["result_net"].apply(lambda x: 2 if x == 1 else 1)
            elif "result" in df.columns:
                df["result"] = pd.to_numeric(df["result"], errors="coerce")
                sample_weight = df["result"].apply(lambda x: 2 if x == 1 else 1)
            else:
                sample_weight = None

            if sample_weight is not None:
                self.model.fit(X, y, sample_weight=sample_weight)
            else:
                self.model.fit(X, y)

        except Exception as e:
            logger.error(f"🔥 Error entrenando {self.mode}: {e}")
            return False

        self.metrics = {
            "samples": int(len(df)),
            "classes": sorted(y.unique().tolist()),
            "n_classes": int(unique_classes),
            "class_distribution": y.value_counts().to_dict(),
        }

        try:
            import joblib
            joblib.dump(self.model, self.get_model_path())
            self.last_train = time.time()
        except Exception as e:
            logger.error(f"🔥 Error guardando {self.mode}: {e}")
            return False

        logger.info(f"✅ {self.mode} selector entrenado y guardado")
        return True

    def predict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recomienda estrategia o modo de riesgo.
        """
        self.auto_train()

        if self.model is None:
            return self._fallback_suggestion(data)

        try:
            features = self._extract_features(data)
            X = pd.DataFrame([features])

            suggestion = self.model.predict(X)[0]

            prob_dict = {}
            confidence = 0.5

            if hasattr(self.model, "predict_proba"):
                probabilities = self.model.predict_proba(X)[0]
                classes = self.model.classes_
                prob_dict = {
                    str(cls): float(prob)
                    for cls, prob in zip(classes, probabilities)
                }
                confidence = max(prob_dict.values()) if prob_dict else 0.5

            return {
                "suggestion": suggestion,
                "confidence": float(confidence),
                "all_probabilities": prob_dict,
                "model": f"{self.mode}_selector",
                "fallback": False,
                "features_used": features,
            }

        except Exception as e:
            logger.error(f"🔥 Error en predicción {self.mode}: {e}")
            return self._fallback_suggestion(data)

    def _extract_features(self, data: Dict[str, Any]) -> Dict[str, float]:
        """
        Extrae features del input.
        """
        return {
            "rsi": float(data.get("rsi", 50)),
            "volume": float(data.get("volume", 1)),
            "trend": int(data.get("trend", 0)),
            "momentum": float(data.get("momentum", 0)),
            "hour": int(data.get("hour", 0)),
            "day_of_week": int(data.get("day_of_week", 0)),
            "signal_confidence": float(data.get("signal_confidence", 0)),
            "atr": float(data.get("atr", 0)),
            "market_regime_num": FeatureEncoder.market_regime(
                data.get("market_regime")
            ),
            "volatility_context_num": FeatureEncoder.volatility(
                data.get("volatility_context")
            ),
        }

    def _fallback_suggestion(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fallback cuando no hay modelo entrenado.
        """
        regime = str(data.get("market_regime", "")).lower()
        volatility = str(data.get("volatility_context", "")).lower()
        rsi = float(data.get("rsi", 50))

        if self.mode == "strategy":
            if regime in ["bull", "alcista"] and rsi < 40:
                suggestion = "dip_buying"
                reason = "mercado alcista con RSI bajo"
            elif regime in ["bear", "bajista"]:
                suggestion = "short_breakout"
                reason = "mercado bajista"
            elif volatility in ["high", "alta"]:
                suggestion = "volatility_scalp"
                reason = "alta volatilidad"
            else:
                suggestion = "trend_following"
                reason = "default"

            return {
                "suggestion": suggestion,
                "confidence": 0.5,
                "model": "fallback_rules",
                "fallback": True,
                "reason": reason,
            }

        if volatility in ["high", "alta"]:
            suggestion = "conservative"
            reason = "alta volatilidad, reducir riesgo"
        elif regime in ["bear", "bajista"]:
            suggestion = "conservative"
            reason = "mercado bajista"
        elif rsi < 30 or rsi > 70:
            suggestion = "aggressive"
            reason = "condiciones extremas, oportunidad"
        else:
            suggestion = "normal"
            reason = "condiciones normales"

        return {
            "suggestion": suggestion,
            "confidence": 0.5,
            "model": "fallback_rules",
            "fallback": True,
            "reason": reason,
        }

    def get_all_strategies(self) -> List[str]:
        """
        Retorna todas las clases conocidas por el modelo.
        """
        if self.model is None or not hasattr(self.model, "classes_"):
            return []
        return sorted([str(x) for x in self.model.classes_.tolist()])

    def get_strategy_performance(self) -> List[Dict[str, Any]]:
        """
        Analiza performance por estrategia o riesgo basado en datos históricos.
        """
        if not hasattr(self.config, "data_file"):
            return []

        try:
            df = pd.read_csv(self.config.data_file)
            df = self.engineer_features(df)
            df = self.prepare_target(df)

            result_col = None
            if "result_net" in df.columns:
                result_col = "result_net"
            elif "result" in df.columns:
                result_col = "result"

            if result_col is None:
                return []

            df[result_col] = pd.to_numeric(df[result_col], errors="coerce")

            performance = df.groupby(self.target_column).agg({
                result_col: ["count", "mean", "sum"]
            }).reset_index()

            performance.columns = [
                self.target_column,
                "total_trades",
                "win_rate",
                "total_wins",
            ]

            return performance.to_dict("records")

        except Exception as e:
            logger.error(f"🔥 Error analizando performance {self.mode}: {e}")
            return []