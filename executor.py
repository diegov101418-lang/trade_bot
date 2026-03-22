from binance.client import Client
import os
from dotenv import load_dotenv

load_dotenv()

client = Client(
    os.getenv("API_KEY"),
    os.getenv("API_SECRET")
)


def buy(symbol, quantity):

    try:
        order = client.order_market_buy(
            symbol=symbol,
            quantity=round(quantity, 5)
        )
        print("✅ BUY REAL:", order)
    except Exception as e:
        print("❌ Error BUY:", e)


def sell(symbol, quantity):

    try:
        order = client.order_market_sell(
            symbol=symbol,
            quantity=round(quantity, 5)
        )
        print("✅ SELL REAL:", order)
    except Exception as e:
        print("❌ Error SELL:", e)