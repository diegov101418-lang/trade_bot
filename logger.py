import csv
import time
from datetime import datetime
FILE_NAME = "trades_dataset.csv"


def log_trade(symbol, action, price, quantity, rsi, ma50, ma200, volume, result):

    timestamp = int(time.time())
    now = datetime.utcnow

    row = {
        "timestamp": now.isofornat(),
        "symbol": symbol,
        "action": action,
        "price": price,
        "quantity": quantity,
        "rsi": rsi,
        "ma50": ma50,
        "ma200": ma200,
        "volume": volume,
        "hour": now.hour,
        "result": result 
        }
    

    try:

        with open(FILE_NAME, "a", newline="") as f:

            writer = csv.writer(f)

            writer.writerow(row)

    except Exception as e:

        print("Error guardando trade:", e)