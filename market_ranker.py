from indicators import get_indicators


def rank_symbols(symbols):

    ranked = []

    for symbol in symbols:

        try:
            df = get_indicators(symbol)

            if df is None or len(df) < 50:
                continue

            last = df.iloc[-1]

            rsi = last["rsi"]
            volume = last["volume"]

            score = 0

            if rsi < 40:
                score += 2

            if volume > df["volume"].mean():
                score += 2

            if last["close"] > last["ma50"]:
                score += 1

            ranked.append({
                "symbol": symbol,
                "score": score
            })

        except:
            continue

    ranked.sort(key=lambda x: x["score"], reverse=True)

    return ranked