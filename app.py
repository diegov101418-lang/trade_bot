from flask import Flask, render_template, jsonify, redirect
import csv
import time

from config import (
    is_running,
    set_running,
    set_mode,
    get_mode,
    set_strategy,
    get_strategy_name
)

from position_manager import get_open_positions
from performance import get_performance
from portfolio import (
    get_balance,
    get_free_balance,
    get_used_balance,
    get_equity
)
from indicators import get_indicators

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True


# =========================
# TRADES
# =========================
def get_trades():
    trades = []

    try:
        with open("trades_dataset.csv", "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                trades.append(row)
    except Exception as e:
        print(f"⚠ Error leyendo trades: {e}")

    return trades[-20:]


# =========================
# STATS
# =========================
def get_stats():
    wins = 0
    losses = 0

    try:
        with open("trades_dataset.csv", "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                raw = row.get("result", "")

                if raw == "":
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
        "winrate": round(winrate, 2)
    }


# =========================
# POSICIONES EN VIVO
# =========================
def get_live_positions():
    positions = get_open_positions()
    live_positions = []

    for pos in positions:
        enriched = dict(pos)

        try:
            symbol = pos["symbol"]
            df = get_indicators(symbol)

            if df is not None and len(df) > 0:
                last = df.iloc[-1]
                current_price = float(last["close"])
                enriched["current_price"] = current_price

                entry = float(pos.get("entry_price", 0))
                qty = float(pos.get("quantity", 0))

                if entry > 0 and qty > 0:
                    pnl = (current_price - entry) * qty
                    pnl_pct = ((current_price - entry) / entry) * 100
                else:
                    pnl = 0
                    pnl_pct = 0

                enriched["pnl"] = round(pnl, 4)
                enriched["pnl_pct"] = round(pnl_pct, 2)

        except Exception as e:
            print(f"⚠ Error actualizando posición {pos.get('symbol')}: {e}")
            enriched["current_price"] = None
            enriched["pnl"] = 0
            enriched["pnl_pct"] = 0

        live_positions.append(enriched)

    return live_positions


# =========================
# DASHBOARD
# =========================
@app.route("/")
def dashboard():
    performance = get_performance()

    portfolio_data = {
        "balance": get_balance(),
        "free_balance": get_free_balance(),
        "used_balance": get_used_balance(),
        "equity": get_equity()
    }

    return render_template(
        "dashboard.html",
        positions=get_live_positions(),
        trades=get_trades(),
        running=is_running(),
        mode=get_mode(),
        strategy=get_strategy_name(),
        performance=performance,
        portfolio=portfolio_data,
        stats=get_stats()
    )


# =========================
# API
# =========================
@app.route("/api/data")
def api_data():
    performance = get_performance()

    return jsonify({
        "positions": get_live_positions(),
        "trades": get_trades(),

        "balance": get_balance(),
        "free_balance": get_free_balance(),
        "used_balance": get_used_balance(),
        "equity": get_equity(),

        "performance": performance,
        "history": performance.get("history", []),
        "stats": get_stats(),

        "mode": get_mode(),
        "running": is_running(),
        "strategy": get_strategy_name(),
        "time": time.time()
    })


# =========================
# CONTROLES
# =========================
@app.route("/start")
def start():
    set_running(True)
    return redirect("/")


@app.route("/stop")
def stop():
    set_running(False)
    return redirect("/")


@app.route("/mode/demo")
def demo():
    set_mode("demo")
    return redirect("/")


@app.route("/mode/real")
def real():
    set_mode("real")
    return redirect("/")


# =========================
# ESTRATEGIAS
# =========================
@app.route("/strategy/trend")
def strat_trend():
    set_strategy("trend")
    return redirect("/")


@app.route("/strategy/scalping")
def strat_scalp():
    set_strategy("scalping")
    return redirect("/")


@app.route("/strategy/auto")
def strat_auto():
    set_strategy("auto")
    return redirect("/")


# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)