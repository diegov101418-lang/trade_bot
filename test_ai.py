from AI import TradePredictionManager

manager = TradePredictionManager()

market_data = {
    "rsi": 28,
    "volume": 1.8,
    "trend": 1,
    "momentum": 0.6,
    "hour": 15,
    "day_of_week": 2,
    "signal_confidence": 0.85,
    "atr": 0.025,
    "market_regime": "bull",
    "volatility_context": "medium",
    "liquidity_mode": "normal",
    "ai_context_risk": "normal"
}

result = manager.predict(market_data)
print(result)