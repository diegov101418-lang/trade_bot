def breakout_strategy(data):
    if data["price"] > data["ma50"] and data["volume"] > data["avg_volume"] * 1.5:
        return {
            "type": "BUY",
            "strategy": "breakout",
            "confidence": 0.75
        }

    return None