from flask import Flask, render_template, jsonify, redirect
from analysis_reports.hour_analysis import analyze_by_hour
from analysis_reports.day_analysis import analyze_by_day
from config import (
    is_running,
    set_running,
    set_mode,
    get_mode,
    set_strategy,
    get_strategy_name
)

from services.dashboard_service import get_dashboard_data

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True


# =========================
# DASHBOARD
# =========================
@app.route("/")
def dashboard():
    return render_template(
        "dashboard.html",
        running=is_running(),
        mode=get_mode(),
        strategy=get_strategy_name(),
    )


# =========================
# API
# =========================
@app.route("/api/data")
def api_data():
    data = get_dashboard_data()

    try:
        data["hour_analysis"] = analyze_by_hour()
        data["day_analysis"] = analyze_by_day()
    except Exception as e:
        print(f"⚠ Error en analyze_by_hour: {e}")
        data["hour_analysis"] = []

    return jsonify(data)



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