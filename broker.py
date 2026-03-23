def execute_trade(signal):

    print(f"🔥 Ejecutando {signal['side']} {signal['symbol']}")

    return {
        "symbol": signal["symbol"],
        "side": signal["side"],
        "capital": 100,
        "entry_price": signal["price"]
    }