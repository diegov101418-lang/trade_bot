import json
from config import MAX_POSITIONS

POSITIONS_FILE = "positions.json"


def load_positions():

    try:
        with open(POSITIONS_FILE) as f:
            return json.load(f)

    except:
        return []


def save_positions(positions):

    with open(POSITIONS_FILE, "w") as f:
        json.dump(positions, f, indent=4)


def can_open_new_position():

    positions = load_positions()

    if len(positions) < MAX_POSITIONS:
        return True

    return False


positions = []


def add_position(symbol, price, quantity):

    position = {
        "symbol": symbol,
        "entry_price": price,
        "quantity": quantity
    }

    positions.append(position)

    print(f"Posición abierta: {symbol} | price: {price} | qty: {quantity}")


def get_open_positions():
    return positions


def close_position(symbol, price):

    global positions

    for pos in positions:

        if pos["symbol"] == symbol:

            entry = float(pos["entry_price"])
            qty = float(pos["quantity"])

            pnl = (price - entry) * qty

            print(f"Cerrada {symbol} | PnL: {pnl}")

            positions.remove(pos)
            return