import time

from bot_controller import is_running, get_mode
from scanner import scan_market
from indicators import get_indicators
from breakout_detector import detect_breakout
from market_regime import detect_market
from strategies import bull_strategy, bear_strategy, sideways_strategy
from ai_predictor import predict_trade
from opportunity_scanner import detect_opportunities

from position_manager import (
    can_open_new_position,
    add_position,
    remove_position,
    get_open_positions
)

from telegram_alerts import send_message
from logger import log_trade


# ===============================
# ANALIZAR UNA MONEDA
# ===============================

def process_symbol(symbol):

    try:

        df = get_indicators(symbol)

        if df is None or len(df) < 200:
            return

        rsi = df["rsi"].iloc[-1]
        ma50 = df["ma50"].iloc[-1]
        ma200 = df["ma200"].iloc[-1]
        volume = df["volume"].iloc[-1]
        price = df["close"].iloc[-1]

        market = detect_market(df)
        breakout = detect_breakout(df)

        # estrategia según mercado
        if market == "bull":
            action = bull_strategy(rsi)

        elif market == "bear":
            action = bear_strategy(rsi)

        else:
            action = sideways_strategy(rsi)

        # ruptura fuerte
        if breakout:
            action = "buy"

        # filtro IA
        ai_prediction = predict_trade(rsi, ma50, ma200, volume)

        if ai_prediction == 0:
            action = "wait"

        # ===============================
        # COMPRA
        # ===============================

        if action == "buy":

            if can_open_new_position():

                quantity = 1

                print("📈 Compra detectada:", symbol, price)

                mode = get_mode()

                if mode == "real":
                    # aquí iría la orden real
                    pass

                add_position(symbol, price, quantity)

                send_message(f"🚀 Compra {symbol} a {price}")

                log_trade(
                    symbol,
                    "buy",
                    price,
                    quantity,
                    rsi,
                    ma50,
                    ma200,
                    volume,
                    1
                )

        check_positions()

    except Exception as e:

        print("Error analizando", symbol)
        print("Detalle:", e)


# ===============================
# REVISAR POSICIONES
# ===============================

def check_positions():

    positions = get_open_positions()

    for pos in positions:

        symbol = pos["symbol"]
        entry = pos["entry_price"]
        quantity = pos["quantity"]

        try:

            df = get_indicators(symbol)

            if df is None:
                continue

            price = df["close"].iloc[-1]

            profit = (price - entry) / entry

            take_profit = 0.03
            stop_loss = -0.02

            if profit >= take_profit or profit <= stop_loss:

                print("📉 Cerrando posición", symbol)

                remove_position(symbol)

                send_message(f"📉 Venta {symbol} profit {profit:.2%}")

                log_trade(
                    symbol,
                    "sell",
                    price,
                    quantity,
                    0,
                    0,
                    0,
                    0,
                    profit
                )

        except Exception as e:

            print("Error cerrando posición", symbol, e)


# ===============================
# CICLO DEL BOT
# ===============================

def run_cycle():

    print("\n🔎 Escaneando mercado...")

    symbols = scan_market()

    # detectar oportunidades
    opportunities = detect_opportunities(symbols)

    print("\n🔥 TOP OPORTUNIDADES")

    for op in opportunities[:5]:

        print(
            op["symbol"],
            "| volumen x", op["volume_ratio"],
            "| cambio", op["price_change"], "%"
        )

    # analizar todas las monedas
    for symbol in symbols:

        process_symbol(symbol)


# ===============================
# LOOP PRINCIPAL
# ===============================

def run_bot():

    print("🤖 Bot iniciado")

    while True:

        running = is_running()

        print("Estado bot:", running)

        if not running:

            print("⏸ Bot detenido")
            time.sleep(5)
            continue

        run_cycle()

        time.sleep(10)


# ===============================
# INICIO
# ===============================

if __name__ == "__main__":

    run_bot()