import requests
import pandas as pd


def get_indicators(symbol):

    url = "https://api.binance.com/api/v3/klines"

    params = {
        "symbol": symbol,
        "interval": "5m",
        "limit": 200
    }

    response = requests.get(url, params=params)

    data = response.json()

    df = pd.DataFrame(data)

    # asignar nombres correctos de columnas
    df.columns = [
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "close_time",
        "quote_asset_volume",
        "number_of_trades",
        "taker_buy_base",
        "taker_buy_quote",
        "ignore"
    ]

    # convertir a número
    df["close"] = pd.to_numeric(df["close"])
    df["volume"] = pd.to_numeric(df["volume"])

    # medias móviles
    df["ma50"] = df["close"].rolling(window=50).mean()
    df["ma200"] = df["close"].rolling(window=200).mean()

    # RSI
    delta = df["close"].diff()

    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()

    rs = gain / loss

    df["rsi"] = 100 - (100 / (1 + rs))

    return df