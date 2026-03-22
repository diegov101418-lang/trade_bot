def detect_opportunities(symbols):

    opportunities = []

    for symbol in symbols:

        try:
            from indicators import get_indicators

            df = get_indicators(symbol)

            if df is None or len(df) < 100:
                continue

            last = df.iloc[-1]

            rsi = last["rsi"]
            volume = last["volume"]
            price = last["close"]

            avg_volume = df["volume"].rolling(30).mean().iloc[-1]

            prev_price = df["close"].iloc[-5]
            price_change = (price - prev_price) / prev_price

            score = 0

            if 25 < rsi < 40:
                score += 2

            if volume > avg_volume * 1.3:
                score += 2

            if price_change > 0.005:
                score += 1

            if score >= 3:
                opportunities.append({
                    "symbol": symbol,
                    "score": score
                })

        except Exception as e:
            print("Error en opportunity:", symbol, e)

    opportunities.sort(key=lambda x: x["score"], reverse=True)

    return opportunities
