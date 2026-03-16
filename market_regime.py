def detect_market(df):

    ma50 = df["ma50"].iloc[-1]
    ma200 = df["ma200"].iloc[-1]

    if ma50 > ma200:
        return "bull"

    elif ma50 < ma200:
        return "bear"

    else:
        return "sideways"