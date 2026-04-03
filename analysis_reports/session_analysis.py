import csv
from collections import defaultdict


def analyze_by_session(file="trades_dataset.csv"):
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
                session = str(row.get("market_session", "")).strip()
                result = str(row.get("result", "")).strip()
                pnl_raw = str(row.get("pnl", "")).strip()

                if session == "" or result == "":
                    continue

                try:
                    pnl = float(pnl_raw) if pnl_raw != "" else 0.0
                except Exception:
                    pnl = 0.0

                stats[session]["total"] += 1
                stats[session]["net_pnl"] += pnl

                if result == "1":
                    stats[session]["wins"] += 1
                else:
                    stats[session]["losses"] += 1

    except FileNotFoundError:
        return []
    except Exception as e:
        print(f"⚠ Error en analyze_by_session: {e}")
        return []

    order = ["asia", "europe", "us", "off"]
    output = []

    for session, data in stats.items():
        total = data["total"]
        wins = data["wins"]
        losses = data["losses"]
        net_pnl = data["net_pnl"]

        winrate = (wins / total * 100) if total > 0 else 0
        avg_pnl = (net_pnl / total) if total > 0 else 0

        output.append({
            "session": session,
            "trades": total,
            "wins": wins,
            "losses": losses,
            "winrate": round(winrate, 2),
            "net_pnl": round(net_pnl, 4),
            "avg_pnl": round(avg_pnl, 4),
        })

    return sorted(output, key=lambda x: order.index(x["session"]) if x["session"] in order else 99)