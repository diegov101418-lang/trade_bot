from binance.client import Client
from config import API_KEY, API_SECRET

client = Client(API_KEY, API_SECRET)

import requests

def scan_market():

    url = "https://api.binance.com/api/v3/ticker/24hr"
    data = requests.get(url).json()

    symbols = []

    for coin in data:

        symbol = coin["symbol"]

        if "USDT" in symbol and float(coin["quoteVolume"]) > 1000000:
            symbols.append(symbol)

    return symbols