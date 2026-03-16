import requests

TOKEN = "8708748255:AAFroiDMlqiU64nf73Y_DMBuYoWpPrC0CMI"
CHAT_ID = "6568298551"

def send_message(text):

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    data = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }

    requests.post(url, data=data)


def send_buy_alert(symbol, price, rsi, market):

    message = f"""
🚀 *COMPRA DETECTADA*

Moneda: {symbol}
Precio: {price}

RSI: {rsi}
Tendencia: {market}

Bot activo 🤖
"""

    send_message(message)


def send_sell_alert(symbol, price, profit):

    message = f"""
📉 *VENTA EJECUTADA*

Moneda: {symbol}
Precio: {price}

Ganancia: {profit:.2%}
"""

    send_message(message)