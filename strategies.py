def bull_strategy(rsi):

    if rsi < 35:
        return "buy"

    return "wait"


def bear_strategy(rsi):

    if rsi > 65:
        return "sell"

    return "wait"


def sideways_strategy(rsi):

    if rsi < 30:
        return "buy"

    if rsi > 70:
        return "sell"

    return "wait"