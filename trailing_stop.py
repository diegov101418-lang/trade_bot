def trailing_take_profit(entry, price, highest):

    profit = (price - entry) / entry

    if price > highest:
        highest = price

    drop = (highest - price) / highest

    if profit > 0.02 and drop > 0.01:
        return True, highest

    return False, highest
trailing_data = {}

def update_trailing_stop(symbol, price):

    if symbol not in trailing_data:
        trailing_data[symbol] = {
            "max_price": price
        }
        return

    # actualizar máximo
    if price > trailing_data[symbol]["max_price"]:
        trailing_data[symbol]["max_price"] = price

    max_price = trailing_data[symbol]["max_price"]

    # trailing 2%
    trailing_stop = max_price * 0.98

    if price < trailing_stop:
        print(f"📉 Trailing Stop activado en {symbol}")