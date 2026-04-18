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
    "dataset_version",
    "pnl_gross",
    "fee_entry",
    "fee_exit",
    "fee_total",
    "pnl_net",
    "mfe_pct",
    "mae_pct",
    "result_net",
    "risk_per_trade_used",
    "is_holiday_ar",
    "holiday_name_ar",
    "is_holiday_eu",
    "holiday_name_eu",
    "is_holiday_asia",
    "holiday_name_asia",
    "is_good_friday",
    "liquidity_mode",
    "ai_trade_decision",
    "ai_context_risk",
    "trade_filter_reason",
        "prob_live",
    "prob_historical",
    "prob_final",
    "decision_source",
    "models_agree",
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

    ensure_trades_file()

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
        "dataset_version": data.get("dataset_version", ""),
        "pnl_gross": data.get("pnl_gross", ""),
        "fee_entry": data.get("fee_entry", ""),
        "fee_exit": data.get("fee_exit", ""),
        "fee_total": data.get("fee_total", ""),
        "pnl_net": data.get("pnl_net", ""),
        "mfe_pct": data.get("mfe_pct", ""),
        "mae_pct": data.get("mae_pct", ""),
        "result_net": data.get("result_net"),
        "risk_per_trade_used": data.get("risk_per_trade_used", ""),
        "is_holiday_ar": data.get("is_holiday_ar", ""),
        "holiday_name_ar": data.get("holiday_name_ar", ""),
        "is_holiday_eu": data.get("is_holiday_eu", ""),
        "holiday_name_eu": data.get("holiday_name_eu", ""),
        "is_holiday_asia": data.get("is_holiday_asia", ""),
        "holiday_name_asia": data.get("holiday_name_asia", ""),
        "is_good_friday": data.get("is_good_friday", ""),
        "liquidity_mode": data.get("liquidity_mode", ""),
        "ai_trade_decision": data.get("ai_trade_decision", ""),
        "ai_context_risk": data.get("ai_context_risk", ""),
        "trade_filter_reason": data.get("trade_filter_reason", ""),
        "prob_live": data.get("prob_live", ""),
        "prob_historical": data.get("prob_historical", ""),
        "prob_final": data.get("prob_final", ""),
        "decision_source": data.get("decision_source", ""),
        "models_agree": data.get("models_agree", ""),
    }

    try:
        with open(TRADES_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writerow(row)

        print(f"✅ Trade registrado: {row['symbol']}")
    except Exception as e:
        print(f"❌ Error registrando trade: {e}")


# =========================
# ACTUALIZAR RESULTADO
# =========================
def update_trade_result(
    symbol,
    result,
    pnl,
    mfe=0,
    mae=0,
    fee_entry=0,
    fee_exit=0,
    fee_total=0,
    pnl_net=0,
    result_net=0,
):
    global daily_pnl

    ensure_trades_file()
    rows = []

    try:
        with open(TRADES_FILE, "r", newline="", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except FileNotFoundError:
        return

    updated = False

    for row in reversed(rows):
        if row.get("symbol") == symbol and str(row.get("result", "")).strip() == "":
            row["result"] = result
            row["pnl"] = pnl
            row["pnl_gross"] = pnl
            row["mfe_pct"] = mfe
            row["mae_pct"] = mae
            row["fee_entry"] = fee_entry
            row["fee_exit"] = fee_exit
            row["fee_total"] = fee_total
            row["pnl_net"] = pnl_net
            row["result_net"] = result_net
            updated = True
            break

    if not updated:
        print(f"⚠ No se encontró trade abierto para actualizar: {symbol}")
        return

    try:
        with open(TRADES_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)
    except Exception as e:
        print(f"❌ Error reescribiendo trades_dataset.csv: {e}")
        return

    try:
        daily_pnl += float(pnl_net if pnl_net != "" else pnl)
    except Exception:
        pass


# =========================
# WINRATE
# =========================
def get_winrate():
    wins = 0
    losses = 0

    try:
        with open(TRADES_FILE, "r", newline="", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)

            for row in reader:
                raw = str(row.get("result", "")).strip()

                if raw == "":
                    continue

                try:
                    result = int(float(raw))
                except Exception:
                    continue

                if result == 1:
                    wins += 1
                else:
                    losses += 1

    except Exception as e:
        print(f"⚠ Error calculando winrate: {e}")
        return None

    total = wins + losses

    if total == 0:
        return None

    return wins / total


def get_total_closed_trades():
    total = 0

    try:
        with open(TRADES_FILE, "r", newline="", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)

            for row in reader:
                if str(row.get("result", "")).strip() != "":
                    total += 1

    except Exception as e:
        print(f"⚠ Error contando trades cerrados: {e}")
        return 0

    return total


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