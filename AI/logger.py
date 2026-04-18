import csv
import os
import time

AI_LOG_FILE = "ai_decision_log.csv"

FIELDNAMES = [
    "timestamp",
    "scenario_name",
    "rsi",
    "volume",
    "trend",
    "momentum",
    "hour",
    "day_of_week",
    "signal_confidence",
    "atr",
    "market_regime",
    "volatility_context",
    "liquidity_mode",
    "ai_context_risk",
    "historical_prediction",
    "historical_probability_win",
    "historical_model",
    "live_prediction",
    "live_probability_win",
    "live_model",
    "manager_prediction",
    "manager_probability_win",
    "manager_probability_loss",
    "manager_confidence",
    "manager_model",
    "manager_mode",
    "strategy_suggestion",
    "risk_suggestion",
]


def ensure_ai_log_file():
    if not os.path.exists(AI_LOG_FILE) or os.path.getsize(AI_LOG_FILE) == 0:
        with open(AI_LOG_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()


def log_ai_decision(
    scenario_name: str,
    input_data: dict,
    historical_result: dict,
    live_result: dict,
    manager_result: dict,
    strategy_result: dict,
):
    ensure_ai_log_file()

    row = {
        "timestamp": int(time.time()),
        "scenario_name": scenario_name,
        "rsi": input_data.get("rsi", ""),
        "volume": input_data.get("volume", ""),
        "trend": input_data.get("trend", ""),
        "momentum": input_data.get("momentum", ""),
        "hour": input_data.get("hour", ""),
        "day_of_week": input_data.get("day_of_week", ""),
        "signal_confidence": input_data.get("signal_confidence", ""),
        "atr": input_data.get("atr", ""),
        "market_regime": input_data.get("market_regime", ""),
        "volatility_context": input_data.get("volatility_context", ""),
        "liquidity_mode": input_data.get("liquidity_mode", ""),
        "ai_context_risk": input_data.get("ai_context_risk", ""),
        "historical_prediction": historical_result.get("prediction", ""),
        "historical_probability_win": historical_result.get("probability_win", ""),
        "historical_model": historical_result.get("model", ""),
        "live_prediction": live_result.get("prediction", ""),
        "live_probability_win": live_result.get("probability_win", ""),
        "live_model": live_result.get("model", ""),
        "manager_prediction": manager_result.get("prediction", ""),
        "manager_probability_win": manager_result.get("probability_win", ""),
        "manager_probability_loss": manager_result.get("probability_loss", ""),
        "manager_confidence": manager_result.get("confidence", ""),
        "manager_model": manager_result.get("model", ""),
        "manager_mode": manager_result.get("manager_mode", ""),
        "strategy_suggestion": strategy_result.get("strategy_suggestion", ""),
        "risk_suggestion": strategy_result.get("risk_suggestion", ""),
    }

    with open(AI_LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writerow(row)