import csv
from collections import defaultdict


def analyze_holidays(file="trades_dataset.csv"):
    stats = defaultdict(lambda: {
        "wins": 0,
        "losses": 0,
        "total": 0,
        "net_pnl": 0.0
    })

    try:
        with open(file, newline="", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)

            for row in reader:
                result = str(row.get("result", "")).strip()
                pnl_raw = str(row.get("pnl", "")).strip()
                is_holiday = str(row.get("is_holiday_us", "")).strip()

                if result == "":
                    continue

                if is_holiday == "":
                    continue

                try:
                    pnl = float(pnl_raw) if pnl_raw != "" else 0.0
                except Exception:
                    pnl = 0.0

                key = "holiday" if is_holiday == "1" else "normal"

                stats[key]["total"] += 1
                stats[key]["net_pnl"] += pnl

                if result == "1":
                    stats[key]["wins"] += 1
                else:
                    stats[key]["losses"] += 1

    except FileNotFoundError:
        return []
    except Exception as e:
        print(f"⚠ Error en analyze_holidays: {e}")
        return []

    output = []

    for key, data in stats.items():
        total = data["total"]
        wins = data["wins"]
        losses = data["losses"]
        net_pnl = data["net_pnl"]

        winrate = (wins / total * 100) if total > 0 else 0
        avg_pnl = (net_pnl / total) if total > 0 else 0

        output.append({
            "holiday_type": key,
            "trades": total,
            "wins": wins,
            "losses": losses,
            "winrate": round(winrate, 2),
            "net_pnl": round(net_pnl, 4),
            "avg_pnl": round(avg_pnl, 4),
        })

    order = ["normal", "holiday"]
    return sorted(output, key=lambda x: order.index(x["holiday_type"]) if x["holiday_type"] in order else 99)