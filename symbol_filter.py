import csv
import os

TRADES_FILE = "trades_dataset.csv"


def load_closed_trades():
    if not os.path.exists(TRADES_FILE):
        return []

    rows = []
    try:
        with open(TRADES_FILE, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                raw_result = str(row.get("result", "")).strip()
                raw_pnl = str(row.get("pnl", "")).strip()

                if raw_result == "":
                    continue

                try:
                    result = int(float(raw_result))
                except:
                    continue

                try:
                    pnl = float(raw_pnl) if raw_pnl != "" else 0.0
                except:
                    pnl = 0.0

                rows.append({
                    "symbol": row.get("symbol", ""),
                    "result": result,
                    "pnl": pnl
                })
    except Exception as e:
        print(f"⚠ Error leyendo trades para filtro de símbolos: {e}")

    return rows


def get_symbol_stats(symbol):
    trades = [t for t in load_closed_trades() if t["symbol"] == symbol]

    if not trades:
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "winrate": 0,
            "net_pnl": 0,
            "avg_pnl": 0
        }

    wins = sum(1 for t in trades if t["result"] == 1)
    losses = sum(1 for t in trades if t["result"] == 0)
    net_pnl = sum(t["pnl"] for t in trades)
    avg_pnl = net_pnl / len(trades) if trades else 0
    winrate = wins / len(trades) if trades else 0

    return {
        "trades": len(trades),
        "wins": wins,
        "losses": losses,
        "winrate": round(winrate, 4),
        "net_pnl": round(net_pnl, 4),
        "avg_pnl": round(avg_pnl, 4)
    }


def symbol_is_blocked(symbol, min_trades=5, min_winrate=0.35, min_net_pnl=0):
    stats = get_symbol_stats(symbol)

    if stats["trades"] < min_trades:
        return False

    if stats["winrate"] < min_winrate and stats["net_pnl"] <= min_net_pnl:
        return True

    return False


def get_bad_symbols(min_trades=5, min_winrate=0.35, min_net_pnl=0):
    trades = load_closed_trades()
    symbols = sorted(set(t["symbol"] for t in trades if t["symbol"]))

    bad = []
    for symbol in symbols:
        if symbol_is_blocked(symbol, min_trades=min_trades, min_winrate=min_winrate, min_net_pnl=min_net_pnl):
            bad.append(symbol)

    return bad