from backtester import get_historical_data
import numpy as np


def run_strategy(df, ma_period):

    balance = 1000
    position = 0
    entry_price = 0

    for i in range(ma_period, len(df)):

        price = df["close"].iloc[i]

        ma = df["close"].iloc[i-ma_period:i].mean()

        if price > ma and position == 0:

            position = balance / price
            entry_price = price
            balance = 0

        elif price < ma and position > 0:

            balance = position * price
            position = 0

    if position > 0:
        balance = position * price

    return balance


def optimize(symbol):

    df = get_historical_data(symbol)

    best_balance = 0
    best_ma = None

    for ma in range(10, 100):

        result = run_strategy(df, ma)

        print("MA", ma, "->", result)

        if result > best_balance:

            best_balance = result
            best_ma = ma

    print("\nMejor configuración encontrada:")
    print("Media móvil:", best_ma)
    print("Balance final:", best_balance)


if __name__ == "__main__":

    optimize("BTCUSDT")