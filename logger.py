import csv
import time

FILE_NAME = "trades_dataset.csv"


def log_trade(symbol, action, price, quantity, rsi, ma50, ma200, volume, result):

    timestamp = int(time.time())

    row = [
        timestamp,
        symbol,
        action,
        price,
        quantity,
        rsi,
        ma50,
        ma200,
        volume,
        result
    ]

    try:

        with open(FILE_NAME, "a", newline="") as f:

            writer = csv.writer(f)

            writer.writerow(row)

    except Exception as e:

        print("Error guardando trade:", e)