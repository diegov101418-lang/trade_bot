from typing import Dict, Any, Tuple
import logging

import pandas as pd

from .config import ModelConfig
from .predictors import TradePredictor
from .historical import HistoricalTradePredictor

logger = logging.getLogger(__name__)


class TradePredictionManager:
    """
    Manager adaptativo v4:
    - histórico como bootstrap
    - live como modelo principal cuando madura
    - pesos dinámicos según performance reciente
    - overrides por fuerza del setup
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
            final = self._blend_predictions(live_result, historical_result, data)

        else:
            mode = "adaptive_live_priority"
            final = self._adaptive_live_priority(live_result, historical_result, data)

        return {
            "prediction": final["prediction"],
            "confidence": final["confidence"],
            "probability_win": final["probability_win"],
            "probability_loss": final["probability_loss"],
            "model": final["model"],
            "fallback": bool(
                live_result.get("fallback", False)
                and historical_result.get("fallback", False)
            ),
            "manager_mode": mode,
            "live_samples": live_samples,
            "live_result": live_result,
            "historical_result": historical_result,
        }

    # =========================
    # LIVE SAMPLES REALES
    # =========================
    def _get_live_samples(self) -> int:
        try:
            df = pd.read_csv(
                self.config.data_file,
                encoding="utf-8",
                on_bad_lines="skip",
                engine="python",
            )

            if "result_net" not in df.columns:
                return 0

            df["result_net"] = pd.to_numeric(df["result_net"], errors="coerce")
            df = df[df["result_net"].isin([0, 1])]

            return int(len(df))

        except Exception as e:
            logger.warning(f"⚠ Error leyendo live samples desde dataset: {e}")
            return 0

    def get_live_sample_count(self) -> int:
        return self._get_live_samples()

    def get_mode(self) -> str:
        live_samples = self._get_live_samples()

        if live_samples < 30:
            return "historical_only"
        if live_samples < 100:
            return "blended"
        return "adaptive_live_priority"

    # =========================
    # SETUP STRENGTH
    # =========================
    def _get_setup_strength(self, data: Dict[str, Any]) -> str:
        rsi = float(data.get("rsi", 50))
        volume = float(data.get("volume", 1))
        trend = int(data.get("trend", 0))
        momentum = float(data.get("momentum", 0))
        signal_conf = float(data.get("signal_confidence", 0))
        market_regime = str(data.get("market_regime", "")).lower().strip()
        liquidity_mode = str(data.get("liquidity_mode", "")).lower().strip()
        volatility = str(data.get("volatility_context", "")).lower().strip()

        score = 0

        if rsi <= 30:
            score += 1
        if volume >= 1.5:
            score += 1
        if trend == 1:
            score += 1
        if momentum > 0:
            score += 1
        if signal_conf >= 0.85:
            score += 2
        elif signal_conf >= 0.75:
            score += 1
        if market_regime == "bull":
            score += 1
        if liquidity_mode == "normal":
            score += 1
        if volatility == "medium":
            score += 1

        if score >= 7:
            return "strong"
        if score >= 4:
            return "medium"
        return "weak"

    # =========================
    # PERFORMANCE RECIENTE
    # =========================
    def _get_recent_model_scores(self, window: int = 80) -> Tuple[float, float]:
        """
        Devuelve score reciente (0..1) para:
        - live
        - historical

        Usa el dataset live enriquecido, si existen columnas sombra:
        - shadow_prediction
        - prob_live
        - prob_historical
        - result_net
        """
        try:
            df = pd.read_csv(
                "trades_dataset.csv",
                encoding="utf-8",
                on_bad_lines="skip",
                engine="python",
            )

            required = ["result_net", "shadow_prediction", "prob_live", "prob_historical"]
            missing = [c for c in required if c not in df.columns]
            if missing:
                return 0.55, 0.45

            df["result_net"] = pd.to_numeric(df["result_net"], errors="coerce")
            df["shadow_prediction"] = pd.to_numeric(df["shadow_prediction"], errors="coerce")
            df["prob_live"] = pd.to_numeric(df["prob_live"], errors="coerce")
            df["prob_historical"] = pd.to_numeric(df["prob_historical"], errors="coerce")

            df = df[df["result_net"].isin([0, 1])]

            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce")
                df = df.sort_values("timestamp")

            df = df.tail(window)

            if len(df) < 15:
                return 0.55, 0.45

            # score live:
            # 1) acierto direccional de shadow_prediction
            live_acc = (df["shadow_prediction"] == df["result_net"]).mean()

            # 2) calibración suave: prob_live alta debería asociarse a result_net=1
            live_cal = 1.0 - (df["prob_live"] - df["result_net"]).abs().mean()

            # score historical:
            hist_pred = (df["prob_historical"] >= 0.5).astype(int)
            hist_acc = (hist_pred == df["result_net"]).mean()
            hist_cal = 1.0 - (df["prob_historical"] - df["result_net"]).abs().mean()

            live_score = (live_acc * 0.65) + (live_cal * 0.35)
            hist_score = (hist_acc * 0.65) + (hist_cal * 0.35)

            # piso razonable
            live_score = float(max(0.0, min(1.0, live_score)))
            hist_score = float(max(0.0, min(1.0, hist_score)))

            return live_score, hist_score

        except Exception as e:
            logger.warning(f"⚠ Error calculando scores recientes del manager: {e}")
            return 0.55, 0.45

    def _dynamic_weights(self) -> Tuple[float, float]:
        """
        Convierte scores recientes en pesos.
        """
        live_score, hist_score = self._get_recent_model_scores()

        total = live_score + hist_score
        if total <= 0:
            return 0.60, 0.40

        w_live = live_score / total
        w_hist = hist_score / total

        # limitar extremos
        w_live = max(0.35, min(0.85, w_live))
        w_hist = 1.0 - w_live

        return float(w_live), float(w_hist)

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
        hist: Dict[str, Any],
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        live_prob = float(live.get("probability_win", 0.5))
        hist_prob = float(hist.get("probability_win", 0.5))
        strength = self._get_setup_strength(data)

        if strength == "strong":
            w_live, w_hist = 0.70, 0.30
        elif strength == "weak":
            w_live, w_hist = 0.50, 0.50
        else:
            w_live, w_hist = 0.60, 0.40

        final_prob = (live_prob * w_live) + (hist_prob * w_hist)

        return {
            "prediction": 1 if final_prob >= 0.5 else 0,
            "probability_win": final_prob,
            "probability_loss": 1 - final_prob,
            "confidence": abs(final_prob - 0.5) * 2,
            "model": "blended_manager_v4",
        }
    def _adaptive_live_priority(
        self,
        live: Dict[str, Any],
        hist: Dict[str, Any],
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        live_prob = float(live.get("probability_win", 0.5))
        hist_prob = float(hist.get("probability_win", 0.5))

        live_pred = int(live.get("prediction", 0))
        hist_pred = int(hist.get("prediction", 0))

        signal_conf = float(data.get("signal_confidence", 0))
        liquidity_mode = str(data.get("liquidity_mode", "")).lower().strip()
        strength = self._get_setup_strength(data)

        base_w_live, base_w_hist = self._dynamic_weights()

        # =========================
        # 1. SI COINCIDEN
        # =========================
        if live_pred == hist_pred:
            final_prob = (live_prob * base_w_live) + (hist_prob * base_w_hist)

            return {
                "prediction": 1 if final_prob >= 0.5 else 0,
                "probability_win": final_prob,
                "probability_loss": 1 - final_prob,
                "confidence": abs(final_prob - 0.5) * 2,
                "model": "adaptive_live_priority_manager_v4",
            }

        # =========================
        # 2. SI HAY CONFLICTO
        # =========================

        # Setup muy fuerte: favorecer live
        if (
            strength == "strong"
            and signal_conf >= 0.85
            and liquidity_mode == "normal"
        ):
            final_prob = live_prob + (live_prob - hist_prob) * 0.5
            final_prob = max(0.0, min(1.0, final_prob))

        # Histórico muy negativo: proteger
        elif hist_prob <= 0.35:
            final_prob = (live_prob * 0.35) + (hist_prob * 0.65)

        # Live muy fuerte: favorecer live
        elif live_prob >= 0.65:
            final_prob = (live_prob * 0.85) + (hist_prob * 0.15)

        # Setup débil: ser conservador
        elif strength == "weak":
            final_prob = (live_prob * 0.45) + (hist_prob * 0.55)

        # Caso general: usar pesos dinámicos
        else:
            final_prob = (live_prob * base_w_live) + (hist_prob * base_w_hist)

        final_prob = max(0.0, min(1.0, final_prob))

        return {
            "prediction": 1 if final_prob >= 0.5 else 0,
            "probability_win": final_prob,
            "probability_loss": 1 - final_prob,
            "confidence": abs(final_prob - 0.5) * 2,
            "model": "adaptive_live_priority_manager_v4",
        }