import csv
import os
import time

TRADES_FILE = "trades_dataset.csv"

# =========================
# CONFIG
# =========================
MAX_DAILY_TRADES = 30
MAX_RISK_PER_DAY = 0.10

daily_trades = 0
daily_pnl = 0


# =========================
# CSV STRUCTURE
# =========================
FIELDNAMES = [
    "symbol",
    "rsi",
    "volume",
    "trend",
    "momentum",
    "result",
    "pnl",
    "timestamp",
    "hour",
    "day_of_week",
    "signal_confidence",
    "market_regime",
    "strategy_name",
    "risk_mode",
    "atr",
    "volatility_context",
    "market_session",
    "is_holiday_us",
    "holiday_name_us",
    "pnl_gross",
    "fee_entry",
    "fee_exit",
    "fee_total",
    "pnl_net",
    "mfe_pct",
    "mae_pct",
    "risk_per_trade_used",
]

def ensure_trades_file():
    if not os.path.exists(TRADES_FILE) or os.path.getsize(TRADES_FILE) == 0:
        try:
            with open(TRADES_FILE, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
                writer.writeheader()
            print("✅ trades_dataset.csv inicializado")
        except Exception as e:
            print(f"❌ Error creando trades_dataset.csv: {e}")

# =========================
# RESET DIARIO
# =========================
def reset_daily():
    global daily_trades, daily_pnl
    daily_trades = 0
    daily_pnl = 0


# =========================
# CONTROL DE RIESGO
# =========================
def check_limits(balance):
    if daily_trades >= MAX_DAILY_TRADES:
        print("⛔ Límite de trades diario alcanzado")
        return False

    if daily_pnl <= -balance * MAX_RISK_PER_DAY:
        print("⛔ Límite de pérdida diaria alcanzado")
        return False

    return True


# =========================
# REGISTRAR TRADE
# =========================
def register_trade(data=None):
    global daily_trades
    daily_trades += 1

    if not data:
        print("❌ register_trade sin data")
        return

    row = {
    "symbol": data.get("symbol", ""),
    "rsi": data.get("rsi", ""),
    "volume": data.get("volume", ""),
    "trend": data.get("trend", ""),
    "momentum": data.get("momentum", ""),
    "result": data.get("result", ""),
    "pnl": data.get("pnl", ""),
    "timestamp": data.get("timestamp", int(time.time())),
    "hour": data.get("hour", ""),
    "day_of_week": data.get("day_of_week", ""),
    "signal_confidence": data.get("signal_confidence", ""),
    "market_regime": data.get("market_regime", ""),
    "strategy_name": data.get("strategy_name", ""),
    "risk_mode": data.get("risk_mode", ""),
    "atr": data.get("atr", ""),
    "volatility_context": data.get("volatility_context", ""),
    "market_session": data.get("market_session", ""),
    "is_holiday_us": data.get("is_holiday_us", ""),
    "holiday_name_us": data.get("holiday_name_us", ""),
    "pnl_gross": data.get("pnl_gross", ""),
    "fee_entry": data.get("fee_entry", ""),
    "fee_exit": data.get("fee_exit", ""),
    "fee_total": data.get("fee_total", ""),
    "pnl_net": data.get("pnl_net", ""),
    "mfe_pct": data.get("mfe_pct", ""),
    "mae_pct": data.get("mae_pct", ""),
    "risk_per_trade_used": data.get("risk_per_trade_used", ""),
}

    file_exists = os.path.isfile(TRADES_FILE)
    write_header = (not file_exists) or os.path.getsize(TRADES_FILE) == 0

    try:
        with open(TRADES_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)

            if write_header:
                writer.writeheader()

            writer.writerow(row)

        print(f"✅ Trade registrado: {row['symbol']}")

    except Exception as e:
        print(f"❌ Error registrando trade: {e}")

# =========================
# ACTUALIZAR RESULTADO
# =========================
def update_trade_result(symbol, result, pnl, mfe_pct=None, mae_pct=None):
    rows = []

    try:
        with open(TRADES_FILE, "r", newline="", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except FileNotFoundError:
        return

    for row in reversed(rows):
        if row.get("symbol") == symbol and str(row.get("result", "")).strip() == "":
            row["result"] = result
            row["pnl"] = pnl
            row["mfe_pct"] = mfe_pct if mfe_pct is not None else ""
            row["mae_pct"] = mae_pct if mae_pct is not None else ""
            break

    with open(TRADES_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

# =========================
# WINRATE
# =========================
def get_winrate():
    wins = 0
    losses = 0

    try:
        with open(TRADES_FILE, "r", newline="", encoding="utf-8") as f:
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
        print(f"⚠ Error calculando winrate: {e}")

    total = wins + losses
    return (wins / total) if total > 0 else 0


# =========================
# POSITION SIZE
# =========================
def calculate_position_size(balance, risk_per_trade, entry, stop):
    risk_amount = balance * risk_per_trade

    distance = abs(entry - stop)

    if distance == 0:
        return 0

    quantity = risk_amount / distance
    return quantity