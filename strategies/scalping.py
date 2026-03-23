def scalping_strategy(data):

    if data["rsi"] < 45 and data["volume"] > data["avg_volume"] * 1.5:
        return {
            "type": "BUY",
            "strategy": "scalp",
            "confidence": 0.6
        }

    return None