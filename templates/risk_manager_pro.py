from config import RISK_PER_TRADE
import csv
import os
import time

# =========================
# CONTROL DIARIO
# =========================
daily_trades = 0
last_day = None
peak_balance = 0
daily_start_balance = 0


def reset_daily():
    global daily_trades, last_day, daily_start_balance
    daily_trades = 0
    last_day = time.strftime("%Y-%m-%d")
    daily_start_balance = 0


# =========================
# LIMITES
# =========================
def check_limits(balance):

    global daily_trades, last_day, peak_balance

    today = time.strftime("%Y-%m-%d")

    if last_day != today:
        reset_daily()

    # max trades diario
    if daily_trades >= 10:
        print("⛔ Max trades diarios alcanzado")
        return False

    # drawdown
    if peak_balance == 0:
        peak_balance = balance

    drawdown = (balance - peak_balance) / peak_balance

    if drawdown < -0.3:
        print("⛔ Max drawdown alcanzado")
        return False

    return True


def register_trade(data=None):
    global daily_trades
    daily_trades += 1

    # guardar dataset IA
    if data:
        file_exists = os.path.isfile("trades_dataset.csv")

        with open("trades_dataset.csv", "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=data.keys())

            if not file_exists:
                writer.writeheader()

            writer.writerow(data)


# =========================
# WINRATE IA
# =========================
def get_winrate():

    wins = 0
    total = 0

    try:
        with open("trades_dataset.csv") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["result"] != "":
                    total += 1
                    if int(row["result"]) == 1:
                        wins += 1
    except:
        return 0

    return wins / total if total > 0 else 0


def update_trade_result(symbol, result):

    try:
        with open("trades_dataset.csv", "r") as f:
            reader = list(csv.DictReader(f))
    except:
        return

    for row in reversed(reader):
        if row["symbol"] == symbol and row["result"] == "0":
            row["result"] = str(result)
            break

    with open("trades_dataset.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=reader[0].keys())
        writer.writeheader()
        writer.writerows(reader)