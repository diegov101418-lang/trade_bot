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


def add_position(symbol, price, quantity):

    positions = load_positions()

    positions.append({
        "symbol": symbol,
        "entry_price": price,
        "quantity": quantity
    })

    save_positions(positions)


def remove_position(symbol):

    positions = load_positions()

    positions = [p for p in positions if p["symbol"] != symbol]

    save_positions(positions)


def get_open_positions():

    return load_positions()