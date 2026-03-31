import csv
from collections import defaultdict
from datetime import datetime

def analyze_by_day(file="trades_dataset.csv"):
    stats = defaultdict(lambda: {"wins": 0, "losses": 0, "total": 0})

    try:
        with open(file, newline="", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)

            for row in reader:
                timestamp = row.get("timestamp")
                result = row.get("result")

                if not timestamp or result is None:
                    continue

                try:
                    dt = datetime.fromtimestamp(int(timestamp))
                    day_name = dt.strftime("%A")  # Monday, Sunday, etc
                except:
                    continue

                stats[day_name]["total"] += 1

                if str(result) == "1":
                    stats[day_name]["wins"] += 1
                else:
                    stats[day_name]["losses"] += 1

    except FileNotFoundError:
        return []

    output = []

    for day, data in stats.items():
        total = data["total"]
        wins = data["wins"]
        winrate = (wins / total * 100) if total > 0 else 0

        output.append({
            "day": day,
            "trades": total,
            "winrate": round(winrate, 2)
        })

    # orden de días correcto
    order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    return sorted(output, key=lambda x: order.index(x["day"]) if x["day"] in order else 99)