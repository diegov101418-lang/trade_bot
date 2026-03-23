def trend_strategy(data):

    if data["ma50"] > data["ma200"] and data["rsi"] < 40:
        return {
            "type": "BUY",
            "strategy": "trend",
            "confidence": 0.7
        }

    return None