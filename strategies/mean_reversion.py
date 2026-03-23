def mean_reversion_strategy(data):

    if data["rsi"] < 30:
        return {
            "type": "BUY",
            "strategy": "mean_reversion",
            "confidence": 0.8
        }

    return None