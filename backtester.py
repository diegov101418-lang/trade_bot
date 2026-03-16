from binance.client import Client
import pandas as pd
from config import API_KEY, API_SECRET

client = Client(API_KEY, API_SECRET)


def get_historical_data(symbol):

    klines = client.get_historical_klines(
        symbol,
        Client.KLINE_INTERVAL_5MINUTE,
        "30 days ago UTC"
    )

    df = pd.DataFrame(klines)

    df["close"] = df[4].astype(float)
    df["volume"] = df[5].astype(float)

    return df


def run_backtest(symbol):

    df = get_historical_data(symbol)

    balance = 1000
    position = 0
    entry_price = 0

    trades = []

    for i in range(50, len(df)):

        price = df["close"].iloc[i]

        ma50 = df["close"].iloc[i-50:i].mean()

        rsi = df["close"].diff().iloc[i]

        # señal de compra
        if price > ma50 and rsi > 0 and position == 0:

            position = balance / price
            entry_price = price
            balance = 0

            trades.append(("BUY", price))

        # señal de venta
        elif price < ma50 and position > 0:

            balance = position * price
            position = 0

            trades.append(("SELL", price))

    if position > 0:
        balance = position * price

    return balance, trades


if __name__ == "__main__":

    symbol = "BTCUSDT"

    result, trades = run_backtest(symbol)

    print("Resultado final:", result)

    print("Cantidad de operaciones:", len(trades))