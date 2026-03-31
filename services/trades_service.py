import csv
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRADES_FILE = os.path.join(BASE_DIR, "trades_dataset.csv")


def get_trades(limit=20):
    trades = []

    try:
        with open(TRADES_FILE, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                trades.append(row)
    except Exception as e:
        print(f"⚠ Error leyendo trades: {e}")

    return trades[-limit:]


def get_stats():
    wins = 0
    losses = 0

    try:
        with open(TRADES_FILE, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                raw = row.get("result", "")

                if str(raw).strip() == "":
                    continue

                try:
                    result = int(float(raw))
                except:
                    continue

                if result == 1:
                    wins += 1
                else:
                    losses += 1

    except Exception as e:
        print(f"⚠ Error leyendo stats: {e}")

    total = wins + losses
    winrate = (wins / total * 100) if total > 0 else 0

    return {
        "wins": wins,
        "losses": losses,
        "total": total,
        "winrate": round(winrate, 2),
    }