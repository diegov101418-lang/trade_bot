import requests
import pandas as pd


def get_indicators(symbol):

    try:
        url = "https://api.binance.com/api/v3/klines"

        params = {
            "symbol": symbol,
            "interval": "5m",
            "limit": 200
        }

        response = requests.get(url, params=params, timeout=10)

        if response.status_code != 200:
            print(f"Error API {symbol}: {response.status_code}")
            return None

        data = response.json()

        if not data:
            return None

        df = pd.DataFrame(data)

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

        # convertir tipos
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col])

        # ===============================
        # MEDIAS
        # ===============================
        df["ma50"] = df["close"].rolling(50).mean()
        df["ma200"] = df["close"].rolling(200).mean()

        # ===============================
        # RSI
        # ===============================
        delta = df["close"].diff()

        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()

        rs = avg_gain / avg_loss
        df["rsi"] = 100 - (100 / (1 + rs))

        # ===============================
        # ATR
        # ===============================
        high_low = df["high"] - df["low"]
        high_close = abs(df["high"] - df["close"].shift())
        low_close = abs(df["low"] - df["close"].shift())

        true_range = pd.concat(
            [high_low, high_close, low_close],
            axis=1
        ).max(axis=1)

        df["atr"] = true_range.rolling(14).mean()

        return df

    except Exception as e:
        print(f"Error indicadores {symbol}: {e}")
        return None