import csv
import os
from portfolio import get_balance

TRADES_FILE = "trades_dataset.csv"

INITIAL_BALANCE = 1000


def get_performance():

    balance = INITIAL_BALANCE
    history = []

    total_profit = 0
    total_loss = 0
    wins = 0
    losses = 0
    trades_count = 0

    if not os.path.exists(TRADES_FILE):
        return build_response(balance, history, total_profit, total_loss, wins, losses, trades_count)

    with open(TRADES_FILE, "r") as f:
        reader = csv.DictReader(f)

        for row in reader:

            raw = row.get("result", "")

            # 🔥 ignorar trades sin cerrar
            if raw == "":
                continue

            try:
                result = float(raw)
            except:
                continue

            trades_count += 1

            # actualizar balance
            balance += result
            history.append(balance)

            # stats
            if result > 0:
                total_profit += result
                wins += 1
            elif result < 0:
                total_loss += result
                losses += 1

    return build_response(balance, history, total_profit, total_loss, wins, losses, trades_count)


# =========================
# RESPONSE BUILDER
# =========================
def build_response(balance, history, profit, loss, wins, losses, trades):

    total_trades = wins + losses

    winrate = round((wins / total_trades) * 100, 2) if total_trades > 0 else 0

    return {
        "balance": round(balance, 2),
        "history": history[-100:],  # 🔥 limitar para no laggear el chart
        "profit": round(profit, 2),
        "loss": round(loss, 2),
        "wins": wins,
        "losses": losses,
        "winrate": winrate,
        "trades": trades
    }