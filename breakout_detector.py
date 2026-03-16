def detect_breakout(df):

    last = df["close"].iloc[-1]

    high = df["close"].iloc[-20:].max()

    if last >= high:

        return True

    return False