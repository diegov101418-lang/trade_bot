import csv
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRADES_FILE = os.path.join(BASE_DIR, "trades_dataset.csv")


def sanitize_row(row):
    return {str(k): v for k, v in row.items() if k is not None}


def get_trades(limit=20):
    trades = []

    try:
        with open(TRADES_FILE, "r", newline="", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)

            for row in reader:
                clean_row = sanitize_row(row)
                trades.append(clean_row)

    except Exception as e:
        print(f"⚠ Error leyendo trades: {e}")

    return trades[-limit:]


def get_stats():
    wins = 0
    losses = 0

    try:
        with open(TRADES_FILE, "r", newline="", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)

            for row in reader:
                clean_row = sanitize_row(row)
                raw = clean_row.get("result", "")

                if str(raw).strip() == "":
                    continue

                try:
                    result = int(float(raw))
                except Exception:
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