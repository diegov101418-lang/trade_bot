import os
import json
import pandas as pd
from datetime import datetime

TRADES_FILE = "trades_dataset.csv"
OUTPUT_FILE = "daily_stats.json"


def _safe_float(series, default=0.0):
    return pd.to_numeric(series, errors="coerce").fillna(default)


def _normalize_timestamp(series):
    ts = pd.to_numeric(series, errors="coerce")

    # Si viene en milisegundos, lo pasamos a segundos
    ts = ts.where(ts < 1e12, ts / 1000)

    return pd.to_datetime(ts, unit="s", errors="coerce")


def build_daily_stats():
    """
    Lee trades_dataset.csv y devuelve lista de métricas diarias.
    Solo toma trades cerrados.
    """
    if not os.path.exists(TRADES_FILE):
        return []

    try:
        df = pd.read_csv(TRADES_FILE)
    except Exception as e:
        print(f"⚠ Error leyendo {TRADES_FILE}: {e}")
        return []

    if df.empty:
        return []

    required_min = ["timestamp"]
    for col in required_min:
        if col not in df.columns:
            print(f"⚠ Falta columna requerida: {col}")
            return []

    df = df.copy()

    # Normalización de columnas mínimas
    if "symbol" not in df.columns:
        df["symbol"] = ""

    if "result" not in df.columns:
        df["result"] = ""

    if "pnl" not in df.columns:
        df["pnl"] = 0.0

    if "pnl_net" not in df.columns:
        df["pnl_net"] = df["pnl"]

    if "fee_total" not in df.columns:
        if "fee_total_est" in df.columns:
            df["fee_total"] = df["fee_total_est"]
        else:
            df["fee_total"] = 0.0

    df["datetime"] = _normalize_timestamp(df["timestamp"])
    df = df.dropna(subset=["datetime"])

    if df.empty:
        return []

    df["pnl"] = _safe_float(df["pnl"])
    df["pnl_net"] = _safe_float(df["pnl_net"])
    df["fee_total"] = _safe_float(df["fee_total"])
    df["result_str"] = df["result"].astype(str).str.strip().str.lower()

    # Solo trades cerrados
    closed_df = df[
        (df["result_str"] != "") &
        (df["result_str"] != "open")
    ].copy()

    if closed_df.empty:
        return []

    closed_df["date"] = closed_df["datetime"].dt.strftime("%Y-%m-%d")

    daily_stats = []

    for date, group in closed_df.groupby("date"):
        trades = len(group)
        wins = int((group["pnl_net"] > 0).sum())
        losses = int((group["pnl_net"] < 0).sum())
        breakeven = int((group["pnl_net"] == 0).sum())

        pnl_gross = float(group["pnl"].sum())
        fees = float(group["fee_total"].sum())
        pnl_net = float(group["pnl_net"].sum())

        winrate = (wins / trades * 100) if trades > 0 else 0.0
        avg_trade = (pnl_net / trades) if trades > 0 else 0.0
        best_trade = float(group["pnl_net"].max()) if trades > 0 else 0.0
        worst_trade = float(group["pnl_net"].min()) if trades > 0 else 0.0

        symbols = sorted(
            [s for s in group["symbol"].dropna().astype(str).unique().tolist() if s]
        )

        day_data = {
            "date": date,
            "trades": trades,
            "wins": wins,
            "losses": losses,
            "breakeven": breakeven,
            "winrate": round(winrate, 2),
            "pnl_gross": round(pnl_gross, 4),
            "fees": round(fees, 4),
            "pnl_net": round(pnl_net, 4),
            "avg_trade": round(avg_trade, 4),
            "best_trade": round(best_trade, 4),
            "worst_trade": round(worst_trade, 4),
            "symbols": symbols,
        }

        daily_stats.append(day_data)

    # Más reciente primero
    daily_stats.sort(key=lambda x: x["date"], reverse=True)

    return daily_stats


def save_daily_stats_json(output_file=OUTPUT_FILE):
    """
    Genera daily_stats.json desde trades_dataset.csv
    """
    stats = build_daily_stats()

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=4, ensure_ascii=False)
        print(f"✅ daily stats guardado en {output_file}")
    except Exception as e:
        print(f"⚠ Error guardando {output_file}: {e}")

    return stats


def load_daily_stats_json(output_file=OUTPUT_FILE):
    """
    Lee daily_stats.json si existe.
    """
    if not os.path.exists(output_file):
        return []

    try:
        with open(output_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠ Error leyendo {output_file}: {e}")
        return []
    
def get_today_stats(output_file=OUTPUT_FILE):
    stats = load_daily_stats_json(output_file)

    if not stats:
        return {
            "date": None,
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "breakeven": 0,
            "winrate": 0.0,
            "pnl_gross": 0.0,
            "fees": 0.0,
            "pnl_net": 0.0,
            "avg_trade": 0.0,
            "best_trade": 0.0,
            "worst_trade": 0.0,
            "symbols": [],
        }

    today = datetime.now().strftime("%Y-%m-%d")

    for day in stats:
        if day.get("date") == today:
            return day

    return {
        "date": today,
        "trades": 0,
        "wins": 0,
        "losses": 0,
        "breakeven": 0,
        "winrate": 0.0,
        "pnl_gross": 0.0,
        "fees": 0.0,
        "pnl_net": 0.0,
        "avg_trade": 0.0,
        "best_trade": 0.0,
        "worst_trade": 0.0,
        "symbols": [],
    }