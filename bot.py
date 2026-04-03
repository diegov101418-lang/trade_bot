import time
import holidays
from datetime import datetime, timezone

from risk_manager import (
    check_limits,
    register_trade,
    get_winrate,
    update_trade_result,
    calculate_position_size,
    ensure_trades_file,
)
from indicators import get_indicators
from scanner import scan_market
from market_ranker import rank_symbols
from ai_model import predict_trade
from strategy_manager import evaluate_strategies
from position_manager import (
    add_position,
    close_position,
    get_open_positions,
)
from symbol_filter import symbol_is_blocked, get_symbol_stats

from config import (
    is_running,
    load_best_config,
    RISK_PER_TRADE,
    MAX_POSITIONS,
    get_mode,
    get_strategy_name,
)

from portfolio import get_balance, get_free_balance, lock_balance, unlock_balance
from executor import buy, sell
from ai_auto_trainer import maybe_retrain
from ai_strategy_learner import suggest_context_decision


# =========================
# CALENDARIO / SESIONES
# =========================
us_holidays = holidays.US()


def get_market_session(hour_utc: int) -> str:
    if 0 <= hour_utc < 8:
        return "asia"
    elif 8 <= hour_utc < 13:
        return "europe"
    elif 13 <= hour_utc < 21:
        return "us"
    else:
        return "off"


# =========================
# TRAILING + CONTROL
# =========================
trailing_data = {}
last_trade_time = {}


def update_trailing(symbol, price, atr):
    if symbol not in trailing_data:
        trailing_data[symbol] = {"max_price": price}

    if price > trailing_data[symbol]["max_price"]:
        trailing_data[symbol]["max_price"] = price

    max_price = trailing_data[symbol]["max_price"]
    return price < max_price - (atr * 1.5)


def can_trade(symbol):
    now = time.time()

    if symbol in last_trade_time:
        if now - last_trade_time[symbol] < 300:
            return False

    last_trade_time[symbol] = now
    return True


# =========================
# CONFIG DINÁMICA
# =========================
def get_strategy():
    best = load_best_config()

    if best:
        return best["rsi"], best["tp"], best["sl"]

    return 35, 0.05, -0.02


# =========================
# PROCESAR MONEDA
# =========================
def process_symbol(symbol):
    print(f"Entrando a process_symbol: {symbol}")

    try:
        df = get_indicators(symbol)

        if df is None or len(df) < 50:
            print(f"⚠ {symbol} sin datos suficientes")
            return

        last = df.iloc[-1]

        price = float(last["close"])
        rsi = float(last["rsi"])
        ma50 = float(last["ma50"])
        ma200 = float(last["ma200"])
        volume = float(last["volume"])
        avg_volume = float(df["volume"].mean())
        atr = float(last["atr"])

    except Exception as e:
        print(f"❌ Error datos {symbol}: {e}")
        return

    _, BEST_TP, BEST_SL = get_strategy()

    positions = get_open_positions()
    symbols_open = [p["symbol"] for p in positions]
    mode = get_mode()

    bearish = ma50 < ma200 and price < ma50

    if ma50 > ma200 and price > ma50:
        market_regime = "bull"
    elif bearish:
        market_regime = "bear"
    else:
        market_regime = "sideways"

    atr_pct = (atr / price) * 100 if price > 0 else 0
    volatility_context = "low" if atr_pct < 1 else "medium" if atr_pct < 2.5 else "high"

    recovery = price > ma50 and rsi > 40 and volume > avg_volume
    trend_change = ma50 > ma200 and df["ma50"].iloc[-2] < df["ma200"].iloc[-2]
    bearish_rebound = bearish and rsi < 45 and volume > avg_volume * 1.2

    if symbol not in symbols_open:

        if len(positions) >= MAX_POSITIONS:
            return

        if avg_volume < 150000 or not can_trade(symbol):
            return

        if symbol_is_blocked(symbol):
            return

        now_dt = datetime.now(timezone.utc)
        vol_ratio = volume / avg_volume if avg_volume > 0 else 1

        signals = evaluate_strategies({
            "price": price,
            "rsi": rsi,
            "ma50": ma50,
            "ma200": ma200,
            "volume": volume,
            "avg_volume": avg_volume,
            "momentum": price - ma50,
            "trend": price > ma50,
        })

        if not signals:
            return

        best_signal = max(signals, key=lambda x: x["confidence"])
        signal_confidence = float(best_signal.get("confidence", 0))
        strategy_name = str(best_signal.get("strategy", get_strategy_name()))

        # ================= IA CONTEXTO =================
        ia_context = suggest_context_decision({
            "rsi": rsi,
            "volume": vol_ratio,
            "trend": int(price > ma50),
            "momentum": price - ma50,
            "hour": now_dt.hour,
            "day_of_week": now_dt.weekday(),
            "signal_confidence": signal_confidence,
            "market_regime": market_regime,
            "atr": atr,
            "volatility_context": volatility_context,
        })

        ia_risk = ia_context.get("risk_suggestion")

        # ================= IA DECISIÓN =================
        ai_decision = predict_trade({
            "rsi": rsi,
            "volume": vol_ratio,
            "trend": int(price > ma50),
            "momentum": price - ma50,
            "hour": now_dt.hour,
            "day_of_week": now_dt.weekday(),
            "signal_confidence": signal_confidence,
            "market_regime": market_regime,
            "atr": atr,
            "volatility_context": volatility_context,
        })

        if ai_decision == 0 and signal_confidence < 0.80:
            return

        # ================= RISK MODE =================
        risk_mode = "normal"

        if signal_confidence >= 0.80 and market_regime == "bull":
            risk_mode = "aggressive"
        elif signal_confidence < 0.65:
            risk_mode = "conservative"

        if ia_risk in ["aggressive", "normal", "conservative"]:
            risk_mode = ia_risk

        should_buy = (
            (best_signal["type"] == "BUY" and signal_confidence >= 0.70)
            or recovery or trend_change or bearish_rebound
        )

        if not should_buy:
            return

        try:
            balance_free = get_free_balance()
            if balance_free <= 0:
                return

            stop_loss_price = price * (1 + BEST_SL)

            risk_per_trade_used = RISK_PER_TRADE
            if risk_mode == "conservative":
                risk_per_trade_used *= 0.5
            elif risk_mode == "aggressive":
                risk_per_trade_used *= 1.25

            quantity = calculate_position_size(
                balance=balance_free,
                risk_per_trade=risk_per_trade_used,
                entry=price,
                stop=stop_loss_price,
            )

            if quantity <= 0:
                return

            capital = min(quantity * price, balance_free * 0.2)
            quantity = round(capital / price, 6)

            if not lock_balance(capital):
                return

            add_position(symbol, price, quantity, capital, stop_loss_price)

            now_ts = int(now_dt.timestamp())

            register_trade({
                "symbol": symbol,
                "rsi": rsi,
                "volume": vol_ratio,
                "trend": int(price > ma50),
                "momentum": price - ma50,
                "result": "",
                "pnl": "",
                "timestamp": now_ts,
                "hour": now_dt.hour,
                "day_of_week": now_dt.weekday(),
                "signal_confidence": signal_confidence,
                "market_regime": market_regime,
                "strategy_name": strategy_name,
                "risk_mode": risk_mode,
                "atr": atr,
                "volatility_context": volatility_context,
                "market_session": get_market_session(now_dt.hour),
                "is_holiday_us": int(now_dt.date() in us_holidays),
                "dataset_version": "live_ai_risk_v1",
                "risk_per_trade_used": risk_per_trade_used,
            })

            if mode == "real":
                buy(symbol, quantity)

        except Exception as e:
            print(f"❌ Error al abrir posición: {e}")

    else:
        try:
            pos = next((p for p in positions if p["symbol"] == symbol), None)
            if not pos:
                return

            entry = float(pos["entry_price"])
            quantity = float(pos["quantity"])
            capital = float(pos.get("capital", entry * quantity))

            profit_pct = (price - entry) / entry

            if update_trailing(symbol, price, atr) or profit_pct >= BEST_TP or profit_pct <= BEST_SL:

                pnl_real = close_position(symbol, price)
                unlock_balance(capital, pnl_real)

                result = 1 if pnl_real > 0 else 0
                update_trade_result(symbol, result, pnl_real)

                if mode == "real":
                    sell(symbol, quantity)

                trailing_data.pop(symbol, None)

        except Exception as e:
            print(f"❌ Error cerrando {symbol}: {e}")


# =========================
# LOOP
# =========================
def run_cycle():
    maybe_retrain()

    for pos in get_open_positions():
        process_symbol(pos["symbol"])

    for op in rank_symbols(scan_market())[:3]:
        symbol = op.get("symbol") or op.get("pair")
        if symbol:
            process_symbol(symbol)


def start_bot():
    while True:
        if not is_running():
            time.sleep(5)
            continue

        try:
            run_cycle()
        except Exception as e:
            print(f"🔥 Error: {e}")

        time.sleep(30)


if __name__ == "__main__":
    ensure_trades_file()
    start_bot()