from binance.client import Client
from config import API_KEY, API_SECRET

client = Client(API_KEY, API_SECRET)

def scan_market():

    tickers = client.get_ticker()

    pairs = []

    for t in tickers:

        if "USDT" in t["symbol"]:

            pairs.append(t["symbol"])

    return pairs[:30]