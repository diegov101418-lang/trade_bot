import requests

def get_top_symbols():

    url = "https://api.binance.com/api/v3/ticker/24hr"

    data = requests.get(url).json()

    coins = []

    for coin in data:

        symbol = coin["symbol"]

        if "USDT" not in symbol:
            continue

        volume = float(coin["quoteVolume"])
        change = abs(float(coin["priceChangePercent"]))

        score = volume * change

        coins.append({
            "symbol": symbol,
            "score": score,
            "volume": volume,
            "change": change
        })

    coins.sort(key=lambda x: x["score"], reverse=True)

    return coins[:20]