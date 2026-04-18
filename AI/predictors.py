"""
Modelo predictor de trades - Predice si un trade será exitoso
"""

from typing import Dict, Any, List
import logging
import time

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score

from .core import BaseModel
from .encoders import FeatureEncoder

logger = logging.getLogger(__name__)


class TradePredictor(BaseModel):
    """
    Predice la probabilidad de éxito neto de un trade
    (0 = no rentable neto, 1 = rentable neto).
    """

    _MODEL_FILE = "trade_predictor.pkl"
    _TARGET_COLUMN = "result_net"

    FEATURES_BASE = [
        "rsi",
        "volume",
        "trend",
        "momentum",
        "hour",
        "day_of_week",
        "signal_confidence",
        "atr",
    ]

    FEATURES_ENCODED = [
        "market_regime_num",
        "volatility_context_num",
        "liquidity_mode_num",
        "ai_context_risk_num",
    ]

    @property
    def model_file(self) -> str:
        return self._MODEL_FILE

    @property
    def target_column(self) -> str:
        return self._TARGET_COLUMN

    @property
    def features(self) -> List[str]:
        return self.FEATURES_BASE + self.FEATURES_ENCODED

    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convierte features crudos a formato numérico procesado.
        """
        df = df.copy()

        for col in self.FEATURES_BASE:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df["market_regime_num"] = df["market_regime"].apply(
            FeatureEncoder.market_regime
        )
        df["volatility_context_num"] = df["volatility_context"].apply(
            FeatureEncoder.volatility
        )
        df["liquidity_mode_num"] = df["liquidity_mode"].apply(
            FeatureEncoder.liquidity
        )
        df["ai_context_risk_num"] = df["ai_context_risk"].apply(
            FeatureEncoder.risk
        )

        return df

    def prepare_target(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepara la columna target: result_net debe ser 0 o 1.
        """
        df = df.copy()

        df[self.target_column] = pd.to_numeric(
            df[self.target_column],
            errors="coerce"
        )
        df = df[df[self.target_column].isin([0, 1])]

        if len(df) < self.config.min_samples:
            logger.warning(f"⚠ Trades válidos insuficientes: {len(df)}")

        return df

    def _fit_model(self, df: pd.DataFrame) -> bool:
        """
        Entrena el Random Forest y guarda métricas.
        """
        X = df[self.features]
        y = df[self.target_column].astype(int)

        if y.nunique() < 2:
            logger.warning(f"⚠ Target sin variedad: {sorted(y.unique().tolist())}")
            return False

        logger.info(f"🔄 Validación cruzada ({self.config.cv_folds} folds)...")

        temp_model = RandomForestClassifier(
            n_estimators=self.config.n_estimators,
            max_depth=self.config.max_depth,
            min_samples_leaf=self.config.min_samples_leaf,
            random_state=self.config.random_state,
            n_jobs=-1,
        )

        cv_mean = 0.0
        cv_std = 0.0

        try:
            scores = cross_val_score(
                temp_model,
                X,
                y,
                cv=self.config.cv_folds
            )
            cv_mean = float(scores.mean())
            cv_std = float(scores.std())
        except Exception as e:
            logger.warning(f"⚠ Error en validación cruzada: {e}. Entrenando sin CV...")

        try:
            self.model = temp_model
            self.model.fit(X, y)
        except Exception as e:
            logger.error(f"🔥 Error entrenando TradePredictor: {e}")
            return False

        self.metrics = {
            "cv_accuracy_mean": cv_mean,
            "cv_accuracy_std": cv_std,
            "samples": int(len(df)),
            "positive_rate": float(y.mean()),
            "feature_importance": dict(
                zip(self.features, self.model.feature_importances_.tolist())
            ),
            "class_distribution": y.value_counts().to_dict(),
        }

        try:
            import joblib
            joblib.dump(self.model, self.get_model_path())
            self.last_train = time.time()
        except Exception as e:
            logger.error(f"🔥 Error guardando modelo: {e}")
            return False

        logger.info(
            f"✅ TradePredictor entrenado | "
            f"accuracy: {cv_mean:.3f} (+/- {cv_std * 2:.3f}) | "
            f"samples: {len(df)}"
        )

        importance = self.metrics["feature_importance"]
        top_features = sorted(
            importance.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        logger.info(f"📊 Top features: {top_features}")

        return True

    def predict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predice si un trade será rentable neto.
        """
        self.auto_train()

        if self.model is None:
            return self._fallback_predict(data)

        try:
            features = self._extract_features(data)
            X = pd.DataFrame([features])

            if X.isnull().any().any():
                null_cols = X.columns[X.isnull().any()].tolist()
                logger.warning(f"⚠ Features con NaN: {null_cols}")
                X = X.fillna(0)

            prediction = int(self.model.predict(X)[0])

            probability_win = 0.5
            probability_loss = 0.5
            confidence = 0.5

            if hasattr(self.model, "predict_proba"):
                probabilities = self.model.predict_proba(X)[0]
                classes = list(self.model.classes_)

                prob_map = {
                    int(cls): float(prob)
                    for cls, prob in zip(classes, probabilities)
                }

                probability_loss = prob_map.get(0, 0.0)
                probability_win = prob_map.get(1, 0.0)
                confidence = max(prob_map.values()) if prob_map else 0.5

            return {
                "prediction": prediction,
                "confidence": float(confidence),
                "probability_win": float(probability_win),
                "probability_loss": float(probability_loss),
                "model": "trade_predictor",
                "fallback": False,
                "features_used": features,
            }

        except Exception as e:
            logger.error(f"🔥 Error en predicción: {e}")
            return self._fallback_predict(data)

    def _extract_features(self, data: Dict[str, Any]) -> Dict[str, float]:
        """
        Extrae y normaliza features del input raw.
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
            "liquidity_mode_num": FeatureEncoder.liquidity(
                data.get("liquidity_mode")
            ),
            "ai_context_risk_num": FeatureEncoder.risk(
                data.get("ai_context_risk")
            ),
        }

    def _fallback_predict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fallback basado en reglas cuando el modelo no está disponible.
        """
        score = 0
        reasons = []

        rsi = float(data.get("rsi", 50))
        if rsi < 35:
            score += 1
            reasons.append("rsi_oversold")

        volume = float(data.get("volume", 1))
        if volume > 1.2:
            score += 1
            reasons.append("high_volume")

        trend = int(data.get("trend", 0))
        if trend == 1:
            score += 1
            reasons.append("uptrend")

        momentum = float(data.get("momentum", 0))
        if momentum > 0:
            score += 1
            reasons.append("positive_momentum")

        regime = str(data.get("market_regime", "")).lower()
        if regime in ["bull", "alcista"]:
            score += 1
            reasons.append("bull_market")

        prediction = 1 if score >= 3 else 0
        confidence = score / 5.0

        logger.info(f"⚠ Usando fallback: score={score}/5, reasons={reasons}")

        return {
            "prediction": prediction,
            "confidence": float(confidence),
            "probability_win": float(confidence if prediction == 1 else (1 - confidence)),
            "probability_loss": float((1 - confidence) if prediction == 1 else confidence),
            "model": "fallback_rules",
            "fallback": True,
            "score": score,
            "reasons": reasons,
        }

    def explain_prediction(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Genera una explicación aproximada de la predicción.
        """
        prediction = self.predict(data)

        if prediction.get("fallback"):
            return {
                "explanation": "Predicción basada en reglas (modelo no disponible)",
                "rules_triggered": prediction.get("reasons", []),
            }

        importance = self.metrics.get("feature_importance", {})
        features_used = prediction.get("features_used", {})

        contributions = []
        for feat, value in features_used.items():
            numeric_value = value if isinstance(value, (int, float)) else 0
            contrib = importance.get(feat, 0) * abs(numeric_value)
            contributions.append({
                "feature": feat,
                "value": value,
                "importance": importance.get(feat, 0),
                "contribution": contrib,
            })

        contributions.sort(key=lambda x: x["contribution"], reverse=True)

        return {
            "prediction": prediction["prediction"],
            "confidence": prediction["confidence"],
            "top_contributing_features": contributions[:5],
            "explanation": f"Basado en {len(self.features)} features técnicas y de contexto",
        }