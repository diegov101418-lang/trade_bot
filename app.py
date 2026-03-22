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

app = Flask(__name__)

app.config['TEMPLATES_AUTO_RELOAD'] = True


# =========================
# TRADES
# =========================
def get_trades():

    trades = []

    try:
        with open("trades_dataset.csv", "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                trades.append(row)
    except:
        pass

    return trades[-20:]


# =========================
# STATS
# =========================
def get_stats():

    wins = 0
    losses = 0

    try:
        with open("trades_dataset.csv") as f:

            reader = csv.DictReader(f)

            for row in reader:
                if row["result"] != "":
                    if int(row["result"]) == 1:
                        wins += 1
                    else:
                        losses += 1

    except:
        pass

    total = wins + losses
    winrate = (wins / total * 100) if total > 0 else 0

    return {
        "wins": wins,
        "losses": losses,
        "winrate": round(winrate, 2)
    }


# =========================
# DASHBOARD
# =========================
@app.route("/")
def dashboard():

    performance = get_performance()

    return render_template(
        "dashboard.html",
        positions=get_open_positions(),
        trades=get_trades(),
        running=is_running(),
        mode=get_mode(),
        strategy=get_strategy_name(),
        performance=performance,
        stats=get_stats()
    )


# =========================
# API
# =========================
@app.route("/api/data")
def api_data():

    performance = get_performance()

    return jsonify({
        "positions": get_open_positions(),
        "balance": performance["balance"],
        "performance": performance,
        "history": performance["history"],
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
# ESTRATEGIAS (🔥 NUEVO)
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