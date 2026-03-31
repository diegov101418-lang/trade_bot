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
    "volatility_context"
]

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
def update_trade_result(symbol, result, pnl):
    global daily_pnl

    daily_pnl += pnl

    try:
        rows = []

        with open(TRADES_FILE, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        for row in reversed(rows):
            if row["symbol"] == symbol and row["result"] == "":
                row["result"] = str(result)
                row["pnl"] = str(round(pnl, 4))
                break

        with open(TRADES_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)

    except Exception as e:
        print(f"❌ Error actualizando trade: {e}")


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