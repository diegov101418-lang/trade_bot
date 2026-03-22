import time

from risk_manager import check_limits, register_trade, get_winrate, update_trade_result
from indicators import get_indicators
from scanner import scan_market
from market_ranker import rank_symbols
from ai_model import predict_trade, auto_train

from position_manager import (
    add_position,
    close_position,
    get_open_positions
)

from config import (
    is_running,
    load_best_config,
    RISK_PER_TRADE,
    MAX_POSITIONS,
    get_mode
)

from portfolio import get_balance, update_balance
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

    if price < max_price - (atr * 1.5):
        return True

    return False


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

    try:
        df = get_indicators(symbol)

        if df is None or len(df) < 200:
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
        print(f"❌ Error datos {symbol}:", e)
        return

    BEST_RSI, BEST_TP, BEST_SL = get_strategy()

    positions = get_open_positions()
    symbols_open = [p["symbol"] for p in positions]

    mode = get_mode()

    # =========================
    # BUY
    # =========================
    if symbol not in symbols_open:

        if len(positions) >= MAX_POSITIONS:
            return

        if avg_volume < 100000:
            return

        if not can_trade(symbol):
            return

        print(f"{symbol} | price:{price} rsi:{rsi}")

        # =========================
        # FILTRO MERCADO (PRO)
        # =========================
        bearish = ma50 < ma200 and price < ma50

        if bearish:
            print("📉 Mercado bajista, esperando recuperacion")
            return
        if ma50 < ma200:
            if rsi < 30 and volume > avg_volume * 2:
                print ("Rebote en mercado bajista")
            else:
                return
        
        #Recuperacion
        recovery = (
            price > ma50 and
            rsi > 40 and
            volume > avg_volume
            )

        # =========================
        # IA
        # =========================
        vol_ratio = volume / avg_volume if avg_volume > 0 else 1

        ai_decision = predict_trade({
            "rsi": rsi,
            "volume": vol_ratio,
            "trend": price > ma50,
            "momentum": price - ma50
        })

        if ai_decision == 0:
            print(f"❌ IA bloquea {symbol}")
            return

        # =========================
        # CONDICIONES COMPRA
        # =========================
        if (
            price > ma50 and
            ma50 > ma200 and
            rsi < BEST_RSI and
            volume > avg_volume
        ):

            print(f"🚀 COMPRA: {symbol} {price} | modo: {mode}")

            try:
                balance = get_balance()

                if balance < 10:
                    print("⚠ Balance insuficiente")
                    return

                # =========================
                # WINRATE PROTECTION
                # =========================
                winrate = get_winrate()

                if winrate < 0.5 and len(positions) > 5:
                    print("⚠ IA con bajo rendimiento, filtrando trades")
                    return

                risk_amount = balance * RISK_PER_TRADE

                stop_loss_price = price * (1 + BEST_SL)
                risk_per_unit = abs(price - stop_loss_price)

                if risk_per_unit <= 0:
                    return

                quantity = risk_amount / risk_per_unit
                quantity = round(quantity, 6)

                if quantity <= 0:
                    return

                if not check_limits(balance):
                    print("⛔ Riesgo bloqueado")
                    return

                # =========================
                # ABRIR POSICIÓN
                # =========================
                add_position(symbol, price, quantity)

                # guardar trade IA
                register_trade({
                    "symbol": symbol,
                    "rsi": rsi,
                    "volume": vol_ratio,
                    "trend": int(price > ma50),
                    "momentum": price - ma50,
                    "result": 0
                })

                if mode == "real":
                    buy(symbol, quantity)

            except Exception as e:
                print("❌ Error al abrir posición:", e)

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

            profit_pct = (price - entry) / entry
            pnl = (price - entry) * quantity

            # =========================
            # TRAILING
            # =========================
            if update_trailing(symbol, price, atr):

                print(f"📉 TRAILING STOP: {symbol}")

                close_position(symbol, price)
                update_balance(pnl)

                result = 1 if pnl > 0 else 0
                update_trade_result(symbol, result)

                if mode == "real":
                    sell(symbol, quantity)

                trailing_data.pop(symbol, None)
                return

            # =========================
            # TP / SL
            # =========================
            if profit_pct >= BEST_TP or profit_pct <= BEST_SL:

                print(f"💰 CIERRE: {symbol} Profit: {profit_pct:.4f}")

                close_position(symbol, price)
                update_balance(pnl)

                result = 1 if pnl > 0 else 0
                update_trade_result(symbol, result)

                if mode == "real":
                    sell(symbol, quantity)

                trailing_data.pop(symbol, None)

        except Exception as e:
            print(f"❌ Error cerrando {symbol}:", e)


# =========================
# CICLO PRINCIPAL
# =========================
def run_cycle():

    auto_train()  # 🔥 IA se entrena sola

    print("🔎 Escaneando mercado...")

    for pos in get_open_positions():
        process_symbol(pos["symbol"])

    symbols = scan_market()
    opportunities = rank_symbols(symbols)

    print(f"📊 Oportunidades: {len(opportunities)}")

    for op in opportunities[:5]:
        process_symbol(op["symbol"])


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
            print("🔥 Error:", e)

        time.sleep(30)


# =========================
# MAIN
# =========================
if __name__ == "__main__":
    start_bot()