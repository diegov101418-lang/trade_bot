from flask import Flask, render_template, redirect
from performance import get_performance
import csv

from bot_controller import (
    start_bot,
    stop_bot,
    is_running,
    set_mode,
    get_mode
)

from position_manager import get_open_positions

app = Flask(__name__)


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


@app.route("/")
def dashboard():

    positions = get_open_positions()
    trades = get_trades()
    performance = get_performance()
    signals = []

    return render_template(
        "dashboard.html",
        positions=positions,
        trades=trades,
        running=is_running(),
        mode=get_mode(),
        performance=performance,
        signals=signals
    )


@app.route("/start")
def start():

    start_bot()
    return redirect("/")


@app.route("/stop")
def stop():

    stop_bot()
    return redirect("/")


@app.route("/mode/demo")
def demo():

    set_mode("demo")
    return redirect("/")


@app.route("/mode/real")
def real():

    set_mode("real")
    return redirect("/")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)