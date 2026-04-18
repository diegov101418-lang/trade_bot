from flask import Flask, render_template, jsonify, redirect
from indicators import get_indicators
from services.daily_stats_service import load_daily_stats_json, save_daily_stats_json, get_today_stats
from analysis_reports.session_analysis import analyze_by_session
from analysis_reports.holiday_analysis import analyze_holidays
from analysis_reports.hour_analysis import analyze_by_hour
from analysis_reports.day_analysis import analyze_by_day

from services.daily_snapshot_service import (
    load_daily_snapshots,
    upsert_today_snapshot,
    get_today_snapshot
)

from config import (
    is_running,
    set_running,
    set_mode,
    get_mode,
    set_strategy,
    get_strategy_name
)

from services.dashboard_service import get_dashboard_data

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["TEMPLATES_AUTO_RELOAD"] = True


# =========================
# CHART API
# =========================
@app.route("/api/chart/<symbol>")
def api_chart(symbol):
    df = get_indicators(symbol)

    if df is None or len(df) == 0:
        return jsonify({"candles": [], "ma50": [], "ma200": []})

    candles = []
    ma50 = []
    ma200 = []

    for _, row in df.iterrows():
        try:
            ts = int(row["timestamp"])

            if ts > 1e12:
                ts = int(ts / 1000)

            candles.append({
                "time": ts,
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
            })

            ma50_value = row.get("ma50")
            ma200_value = row.get("ma200")

            if ma50_value == ma50_value:
                ma50.append({
                    "time": ts,
                    "value": float(ma50_value),
                })

            if ma200_value == ma200_value:
                ma200.append({
                    "time": ts,
                    "value": float(ma200_value),
                })

        except Exception as e:
            print(f"Error candle: {e}")

    return jsonify({
        "candles": candles,
        "ma50": ma50,
        "ma200": ma200,
    })


# =========================
# DAILY SNAPSHOTS API
# =========================
@app.route("/api/snapshots/daily")
def api_daily_snapshots():
    try:
        return jsonify(load_daily_snapshots())
    except Exception as e:
        print(f"⚠ Error en api_daily_snapshots: {e}")
        return jsonify([])


@app.route("/api/snapshots/daily/today")
def api_today_snapshot():
    try:
        return jsonify(get_today_snapshot())
    except Exception as e:
        print(f"⚠ Error en api_today_snapshot: {e}")
        return jsonify({}), 500


@app.route("/api/snapshots/daily/update")
def api_update_today_snapshot():
    try:
        return jsonify(upsert_today_snapshot())
    except Exception as e:
        print(f"⚠ Error en api_update_today_snapshot: {e}")
        return jsonify({}), 500
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
# API DATA
# =========================
@app.route("/api/data")
def api_data():
    data = get_dashboard_data()

    try:
        data["hour_analysis"] = analyze_by_hour()
    except Exception as e:
        print(f"⚠ Error en analyze_by_hour: {e}")
        data["hour_analysis"] = []

    try:
        data["day_analysis"] = analyze_by_day()
    except Exception as e:
        print(f"⚠ Error en analyze_by_day: {e}")
        data["day_analysis"] = []

    try:
        data["session_analysis"] = analyze_by_session()
    except Exception as e:
        print(f"⚠ Error en analyze_by_session: {e}")
        data["session_analysis"] = []

    try:
        data["holiday_analysis"] = analyze_holidays()
    except Exception as e:
        print(f"⚠ Error en analyze_holidays: {e}")
        data["holiday_analysis"] = []

    return jsonify(data)
@app.route("/api/stats/daily")
def api_stats_daily():
    return jsonify(load_daily_stats_json())


@app.route("/api/stats/daily/rebuild")
def api_stats_daily_rebuild():
    data = save_daily_stats_json()
    return jsonify(data)

@app.route("/api/stats/today")
def api_stats_today():
    return jsonify(get_today_stats())
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)