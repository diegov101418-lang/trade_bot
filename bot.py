import time

from risk_manager import (
    check_limits,
    register_trade,
    get_winrate,
    update_trade_result,
    calculate_position_size,
)
from indicators import get_indicators
from scanner import scan_market
from market_ranker import rank_symbols
from ai_model import predict_trade, auto_train
from strategy_manager import evaluate_strategies
from position_manager import (
    add_position,
    close_position,
    get_open_positions,
)

from config import (
    is_running,
    load_best_config,
    RISK_PER_TRADE,
    MAX_POSITIONS,
    get_mode,
)

from portfolio import get_balance, lock_balance, unlock_balance
from executor import buy, sell


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

    return 35, 0.04, -0.02


# =========================
# PROCESAR MONEDA
# =========================
def process_symbol(symbol):
    print(f"Entrando a process_symbol: {symbol}")

    recovery = False
    trend_change = False
    bearish_rebound = False
    bearish = False

    try:
        df = get_indicators(symbol)

        if df is None:
            print(f"❌ {symbol} sin datos")
            return

        if len(df) < 50:
            print(f"⚠ {symbol} pocos datos: {len(df)}")
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

    BEST_RSI, BEST_TP, BEST_SL = get_strategy()

    positions = get_open_positions()
    symbols_open = [p["symbol"] for p in positions]
    mode = get_mode()

    # =========================
    # CONTEXTO MERCADO
    # =========================
    bearish = ma50 < ma200 and price < ma50

    recovery = (
        price > ma50 and
        rsi > 40 and
        volume > avg_volume
    )

    trend_change = (
        ma50 > ma200 and
        df["ma50"].iloc[-2] < df["ma200"].iloc[-2] and
        volume > avg_volume
    )

    bearish_rebound = (
        bearish and
        rsi < 45 and
        volume > avg_volume * 1.2
    )

    print("CONDICIONES:")
    print("recovery:", recovery)
    print("trend_change:", trend_change)
    print("bearish_rebound:", bearish_rebound)

    # =========================
    # BUY
    # =========================
    if symbol not in symbols_open:

        if len(positions) >= MAX_POSITIONS:
            print("⛔ Máximo de posiciones alcanzado")
            return

        if avg_volume < 50000:
            print(f"⛔ Volumen promedio bajo: {avg_volume}")
            return

        if not can_trade(symbol):
            print(f"⏳ Cooldown activo para {symbol}")
            return

        print(f"{symbol} | price:{price} rsi:{rsi}")

        if bearish:
            print("📉 Mercado bajista detectado")
            print(f"DEBUG {symbol} | rsi:{rsi} vol:{volume:.2f}")

        if bearish and not bearish_rebound and not trend_change:
            print("📉 Bajista sin entrada válida")
            return

        # =========================
        # IA + ESTRATEGIAS
        # =========================
        vol_ratio = volume / avg_volume if avg_volume > 0 else 1

        data = {
            "price": price,
            "rsi": rsi,
            "ma50": ma50,
            "ma200": ma200,
            "volume": volume,
            "avg_volume": avg_volume,
            "momentum": price - ma50,
            "trend": price > ma50,
        }

        signals = evaluate_strategies(data)

        if not signals:
            print("❌ Sin señales")
            return

        best_signal = max(signals, key=lambda x: x["confidence"])
        print(f"📊 Señal: {best_signal}")

        ai_decision = predict_trade({
            "rsi": rsi,
            "volume": vol_ratio,
            "trend": price > ma50,
            "momentum": price - ma50,
        })

        # En esta etapa conviene no bloquear del todo por IA.
        if ai_decision == 0:
            print("⚠ IA no confirma, pero se sigue evaluando")

        # =========================
        # CONDICIÓN FINAL DE COMPRA
        # =========================
        should_buy = False

        if best_signal["type"] == "BUY":
            should_buy = True

        if recovery or trend_change or bearish_rebound:
            should_buy = True

        if not should_buy:
            print("❌ No hay condición final de compra")
            return

        print(f"🚀 COMPRA: {symbol} {price} | modo: {mode}")

        try:
            balance = get_balance()

            if balance <= 0:
                print("❌ Balance inválido")
                return

            if not check_limits(balance):
                print("⛔ Riesgo bloqueado")
                return

            winrate = get_winrate()
            if winrate < 0.5 and len(positions) > 3:
                print("⚠ IA bajo rendimiento")
                return

            stop_loss_price = price * (1 + BEST_SL)

            quantity = calculate_position_size(
                balance=balance,
                risk_per_trade=RISK_PER_TRADE,
                entry=price,
                stop=stop_loss_price,
            )

            if quantity <= 0:
                print("❌ Quantity inválida")
                return

            # limitar capital máximo por operación
            max_capital = balance * 0.2
            capital = min(quantity * price, max_capital)
            quantity = round(capital / price, 6)

            if quantity <= 0 or capital <= 0:
                print("❌ Capital o quantity inválidos")
                return

            print(f"💰 balance total: {balance}")
            print(f"🔒 intentando usar: {capital}")

            if not lock_balance(capital):
                print("❌ No hay balance disponible")
                return

            add_position(symbol, price, quantity, capital=capital)

            register_trade({
                "symbol": symbol,
                "rsi": rsi,
                "volume": vol_ratio,
                "trend": int(price > ma50),
                "momentum": price - ma50,
                "result": ""
            })

            if mode == "real":
                buy(symbol, quantity)

        except Exception as e:
            print(f"❌ Error al abrir posición: {e}")

    # =========================
    # SELL
    # =========================
    else:
        try:
            pos = next((p for p in positions if p["symbol"] == symbol), None)

            if not pos:
                return

            entry = float(pos["entry_price"])
            quantity = float(pos["quantity"])
            capital = float(pos.get("capital", entry * quantity))

            pnl_estimado = (price - entry) * quantity
            profit_pct = (price - entry) / entry

            if update_trailing(symbol, price, atr):
                print(f"📉 TRAILING STOP: {symbol}")

                pnl_real = close_position(symbol, price)
                unlock_balance(capital, pnl_real)

                result = 1 if pnl_real > 0 else 0
                update_trade_result(symbol, result)

                if mode == "real":
                    sell(symbol, quantity)

                trailing_data.pop(symbol, None)
                return

            if profit_pct >= BEST_TP or profit_pct <= BEST_SL:
                print(f"💰 CIERRE: {symbol} Profit: {profit_pct:.4f}")

                pnl_real = close_position(symbol, price)
                unlock_balance(capital, pnl_real)

                result = 1 if pnl_real > 0 else 0
                update_trade_result(symbol, result)

                if mode == "real":
                    sell(symbol, quantity)

                trailing_data.pop(symbol, None)

        except Exception as e:
            print(f"❌ Error cerrando {symbol}: {e}")


# =========================
# CICLO PRINCIPAL
# =========================
def run_cycle():
    auto_train()

    print("🔎 Escaneando mercado...")

    for pos in get_open_positions():
        process_symbol(pos["symbol"])

    symbols = scan_market()
    opportunities = rank_symbols(symbols)

    print(f"📊 Oportunidades: {len(opportunities)}")

    for op in opportunities[:5]:
        print("DEBUG OP:", op)

        symbol = op.get("symbol") or op.get("pair") or op.get("coin")

        if not symbol:
            print("❌ No symbol en:", op)
            continue

        process_symbol(symbol)


# =========================
# LOOP BOT
# =========================
def start_bot():
    print("🤖 BOT INICIADO (controlado por dashboard)")

    while True:
        if not is_running():
            print("⏸ Bot en pausa...")
            time.sleep(5)
            continue

        try:
            run_cycle()
        except Exception as e:
            print(f"🔥 Error: {e}")

        time.sleep(30)


# =========================
# MAIN
# =========================
if __name__ == "__main__":
    start_bot()