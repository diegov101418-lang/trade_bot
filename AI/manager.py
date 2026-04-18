from typing import Dict, Any
import logging

from .config import ModelConfig
from .predictors import TradePredictor
from .historical import HistoricalTradePredictor

logger = logging.getLogger(__name__)


class TradePredictionManager:
    """
    Manager inteligente que combina:
    - modelo histórico
    - modelo live

    Modos:
    - historical_only
    - blended
    - live_priority
    """

    def __init__(self, config: ModelConfig | None = None):
        self.config = config or ModelConfig()
        self.live_model = TradePredictor(self.config)
        self.historical_model = HistoricalTradePredictor(self.config)

    # =========================
    # MAIN
    # =========================
    def predict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        live_result = self.live_model.predict(data)
        historical_result = self.historical_model.predict(data)

        live_samples = self._get_live_samples()

        if live_samples < 30:
            mode = "historical_only"
            final = self._historical_only(historical_result)

        elif live_samples < 100:
            mode = "blended"
            final = self._blend_predictions(live_result, historical_result)

        else:
            mode = "live_priority"
            final = self._live_priority(live_result, historical_result)

        return {
            "prediction": final["prediction"],
            "confidence": final["confidence"],
            "probability_win": final["probability_win"],
            "probability_loss": final["probability_loss"],
            "model": final["model"],
            "fallback": bool(
                live_result.get("fallback", False) and
                historical_result.get("fallback", False)
            ),
            "manager_mode": mode,
            "live_samples": live_samples,
            "live_result": live_result,
            "historical_result": historical_result,
        }

    # =========================
    # HELPERS
    # =========================
    def _get_live_samples(self) -> int:
        metrics = self.live_model.get_metrics()
        return int(metrics.get("metrics", {}).get("samples", 0))

    def get_live_sample_count(self) -> int:
        return self._get_live_samples()

    def get_mode(self) -> str:
        live_samples = self._get_live_samples()

        if live_samples < 30:
            return "historical_only"
        if live_samples < 100:
            return "blended"
        return "live_priority"

    # =========================
    # MODES
    # =========================
    def _historical_only(self, hist: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "prediction": int(hist.get("prediction", 0)),
            "confidence": float(hist.get("confidence", 0.5)),
            "probability_win": float(hist.get("probability_win", 0.5)),
            "probability_loss": float(hist.get("probability_loss", 0.5)),
            "model": "historical_trade_predictor",
        }

    def _blend_predictions(
        self,
        live: Dict[str, Any],
        hist: Dict[str, Any]
    ) -> Dict[str, Any]:
        live_prob = float(live.get("probability_win", 0.5))
        hist_prob = float(hist.get("probability_win", 0.5))

        # Mezcla estándar 60/40 a favor de live
        final_prob = (live_prob * 0.6) + (hist_prob * 0.4)

        return {
            "prediction": 1 if final_prob >= 0.5 else 0,
            "probability_win": final_prob,
            "probability_loss": 1 - final_prob,
            "confidence": abs(final_prob - 0.5) * 2,
            "model": "blended_manager",
        }

    def _live_priority(
        self,
        live: Dict[str, Any],
        hist: Dict[str, Any]
    ) -> Dict[str, Any]:
        live_prob = float(live.get("probability_win", 0.5))
        hist_prob = float(hist.get("probability_win", 0.5))

        live_pred = int(live.get("prediction", 0))
        hist_pred = int(hist.get("prediction", 0))

        # =========================
        # CASO 1: ambos coinciden
        # =========================
        if live_pred == hist_pred:
            final_prob = (live_prob * 0.8) + (hist_prob * 0.2)

        # =========================
        # CASO 2: conflicto
        # =========================
        else:
            # live muy fuerte
            if live_prob >= 0.65:
                final_prob = (live_prob * 0.8) + (hist_prob * 0.2)

            # historical muy fuerte del lado negativo
            elif hist_prob <= 0.35:
                final_prob = (live_prob * 0.4) + (hist_prob * 0.6)

            # ninguno domina -> neutralizar un poco
            else:
                final_prob = (live_prob * 0.6) + (hist_prob * 0.4)

        return {
            "prediction": 1 if final_prob >= 0.5 else 0,
            "probability_win": final_prob,
            "probability_loss": 1 - final_prob,
            "confidence": abs(final_prob - 0.5) * 2,
            "model": "live_priority_manager",
        }