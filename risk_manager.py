import csv
import os
import time

from config import (
    RISK_PER_TRADE,
    MAX_DRAWDOWN,
    MAX_DAILY_LOSS,
    MAX_TRADES_PER_DAY,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TRADES_FILE = os.path.join(BASE_DIR, "trades_dataset.csv")

FIELDNAMES = ["symbol", "rsi", "volume", "trend", "momentum", "result", "pnl"]

# =========================
# CONTROL DIARIO
# =========================
daily_trades = 0
last_day = None
peak_balance = 0
daily_start_balance = 0


def reset_daily(balance=0):
    global daily_trades, last_day, daily_start_balance
    daily_trades = 0
    last_day = time.strftime("%Y-%m-%d")
    daily_start_balance = balance


# =========================
# POSITION SIZING
# =========================
def calculate_position_size(balance, risk_per_trade, entry, stop, max_capital_pct=0.2):
    risk_amount = balance * risk_per_trade
    risk_per_unit = abs(entry - stop)

    if risk_per_unit <= 0:
        return 0

    qty = risk_amount / risk_per_unit

    max_capital = balance * max_capital_pct
    capital_used = qty * entry

    if capital_used > max_capital:
        qty = max_capital / entry

    if qty <= 0:
        return 0

    return round(qty, 6)


# =========================
# LIMITES GLOBALES
# =========================
def check_limits(balance):
    global daily_trades, last_day, peak_balance, daily_start_balance

    today = time.strftime("%Y-%m-%d")

    if last_day != today:
        reset_daily(balance)

    if daily_trades >= MAX_TRADES_PER_DAY:
        print("⛔ Max trades diarios alcanzado")
        return False

    if peak_balance == 0 or balance > peak_balance:
        peak_balance = balance

    if peak_balance > 0:
        drawdown = (balance - peak_balance) / peak_balance
        if drawdown <= -MAX_DRAWDOWN:
            print(f"⛔ Max drawdown alcanzado: {drawdown:.2%}")
            return False

    if daily_start_balance > 0:
        daily_loss = (balance - daily_start_balance) / daily_start_balance
        if daily_loss <= -MAX_DAILY_LOSS:
            print(f"⛔ Max pérdida diaria alcanzada: {daily_loss:.2%}")
            return False

    return True


# =========================
# REGISTRAR TRADE
# =========================
def register_trade(data=None):
    global daily_trades
    daily_trades += 1

    print("🧪 register_trade llamado")

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
    }

    print("🧪 Guardando trade en:", TRADES_FILE)
    print("🧪 Row:", row)

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
# WINRATE
# =========================
def get_winrate():
    wins = 0
    total = 0

    if not os.path.exists(TRADES_FILE):
        return 0

    try:
        with open(TRADES_FILE, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                raw = row.get("result", "")

                if raw == "":
                    continue

                try:
                    result = int(float(raw))
                except:
                    continue

                total += 1

                if result == 1:
                    wins += 1

    except Exception as e:
        print(f"⚠ Error leyendo winrate: {e}")
        return 0

    return wins / total if total > 0 else 0


# =========================
# ACTUALIZAR RESULTADO DE TRADE
# =========================
def update_trade_result(symbol, result, pnl=None):
    if not os.path.exists(TRADES_FILE):
        print("⚠ No existe trades_dataset.csv")
        return

    try:
        with open(TRADES_FILE, "r", newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except Exception as e:
        print(f"⚠ Error leyendo trades para update: {e}")
        return

    if not rows:
        print("⚠ CSV vacío al actualizar trade")
        return

    updated = False

    for row in reversed(rows):
        if row.get("symbol") == symbol and row.get("result", "") == "":
            row["result"] = str(result)

            if pnl is not None:
                row["pnl"] = str(round(float(pnl), 6))

            updated = True
            print(f"✅ Trade cerrado actualizado: {symbol} | result={result} | pnl={pnl}")
            break

    if not updated:
        print(f"⚠ No se encontró trade abierto para {symbol}")
        return

    try:
        with open(TRADES_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)
    except Exception as e:
        print(f"⚠ Error guardando trades actualizados: {e}")