import csv
from collections import defaultdict
from datetime import datetime


def analyze_by_hour(file="trades_dataset.csv"):
    stats = defaultdict(lambda: {"wins": 0, "losses": 0, "total": 0})

    try:
        with open(file, newline="", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)

            for row in reader:
                result = row.get("result")
                timestamp = row.get("timestamp")

                if result is None or timestamp is None:
                    continue

                if str(result).strip() == "":
                    continue

                try:
                    ts = int(float(timestamp))
                    hour = datetime.fromtimestamp(ts).hour
                except:
                    continue

                stats[hour]["total"] += 1

                if str(result) == "1":
                    stats[hour]["wins"] += 1
                else:
                    stats[hour]["losses"] += 1

    except FileNotFoundError:
        return []
    except Exception as e:
        print(f"⚠ Error en analyze_by_hour: {e}")
        return []

    output = []

    for hour, data in stats.items():
        total = data["total"]
        wins = data["wins"]
        winrate = (wins / total * 100) if total > 0 else 0

        output.append({
            "hour": hour,
            "trades": total,
            "winrate": round(winrate, 2)
        })

    return sorted(output, key=lambda x: x["hour"])