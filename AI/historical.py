from typing import Dict, Any, List
import logging
import time

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score

from .core import BaseModel
from .encoders import FeatureEncoder

logger = logging.getLogger(__name__)


class HistoricalTradePredictor(BaseModel):
    """
    Predictor histórico:
    aprende desde el dataset histórico usando target = result
    """

    _MODEL_FILE = "historical_trade_predictor.pkl"
    _TARGET_COLUMN = "result"

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
        df = df.copy()
        df[self.target_column] = pd.to_numeric(
            df[self.target_column],
            errors="coerce"
        )
        df = df[df[self.target_column].isin([0, 1])]
        return df

    def _fit_model(self, df: pd.DataFrame) -> bool:
        X = df[self.features]
        y = df[self.target_column].astype(int)

        if y.nunique() < 2:
            logger.warning("⚠ HistoricalTradePredictor sin variedad de target")
            return False

        model = RandomForestClassifier(
            n_estimators=self.config.n_estimators,
            max_depth=self.config.max_depth,
            min_samples_leaf=self.config.min_samples_leaf,
            random_state=self.config.random_state,
            n_jobs=1,
        )

        cv_mean = 0.0
        cv_std = 0.0

        try:
            scores = cross_val_score(
                model,
                X,
                y,
                cv=self.config.cv_folds
            )
            cv_mean = float(scores.mean())
            cv_std = float(scores.std())
        except Exception as e:
            logger.warning(f"⚠ CV historical falló: {e}")

        try:
            model.fit(X, y)
            self.model = model
        except Exception as e:
            logger.error(f"🔥 Error entrenando historical: {e}")
            return False

        self.metrics = {
            "cv_accuracy_mean": cv_mean,
            "cv_accuracy_std": cv_std,
            "samples": int(len(df)),
            "positive_rate": float(y.mean()),
            "feature_importance": dict(
                zip(self.features, self.model.feature_importances_.tolist())
            ),
        }

        try:
            import joblib
            joblib.dump(self.model, self.get_model_path())
            self.last_train = time.time()
            logger.info(
                f"✅ HistoricalTradePredictor entrenado | "
                f"samples={len(df)} | "
                f"cv_mean={cv_mean:.4f} | cv_std={cv_std:.4f}"
            )
            return True
        except Exception as e:
            logger.error(f"🔥 Error guardando modelo historical: {e}")
            return False

    def predict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        self.auto_train()

        if self.model is None:
            return {
                "prediction": 0,
                "confidence": 0.5,
                "probability_win": 0.5,
                "probability_loss": 0.5,
                "model": "historical_fallback",
                "fallback": True,
            }

        try:
            X = pd.DataFrame([{
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
            }])

            pred = int(self.model.predict(X)[0])

            probability_win = 0.5
            probability_loss = 0.5
            confidence = 0.5

            if hasattr(self.model, "predict_proba"):
                probs = self.model.predict_proba(X)[0]
                classes = list(self.model.classes_)
                prob_map = {
                    int(cls): float(prob)
                    for cls, prob in zip(classes, probs)
                }

                probability_win = prob_map.get(1, 0.0)
                probability_loss = prob_map.get(0, 0.0)
                confidence = max(prob_map.values()) if prob_map else 0.5

            return {
                "prediction": pred,
                "confidence": confidence,
                "probability_win": probability_win,
                "probability_loss": probability_loss,
                "model": "historical_trade_predictor",
                "fallback": False,
            }

        except Exception as e:
            logger.error(f"🔥 Error historical predict: {e}")
            return {
                "prediction": 0,
                "confidence": 0.5,
                "probability_win": 0.5,
                "probability_loss": 0.5,
                "model": "historical_fallback",
                "fallback": True,
            }