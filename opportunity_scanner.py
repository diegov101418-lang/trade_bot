import pandas as pd
from indicators import get_indicators


def detect_opportunities(symbols):

    opportunities = []

    for symbol in symbols:

        try:

            df = get_indicators(symbol)

            if df is None or len(df) < 50:
                continue

            volume = df["volume"]
            price = df["close"]

            current_volume = volume.iloc[-1]
            avg_volume = volume.tail(20).mean()

            volume_ratio = current_volume / avg_volume

            price_change = (price.iloc[-1] - price.iloc[-5]) / price.iloc[-5]

            score = volume_ratio + (price_change * 5)

            if volume_ratio > 2:

                opportunities.append({
                    "symbol": symbol,
                    "volume_ratio": round(volume_ratio, 2),
                    "price_change": round(price_change * 100, 2),
                    "score": round(score, 2)
                })

        except:
            continue

    opportunities = sorted(
        opportunities,
        key=lambda x: x["score"],
        reverse=True
    )

    return opportunities[:20]