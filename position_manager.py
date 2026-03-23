import json
import os
from config import MAX_POSITIONS

POSITIONS_FILE = "positions.json"


# =========================
# LOAD / SAVE
# =========================
def load_positions():
    if not os.path.exists(POSITIONS_FILE):
        return []

    try:
        with open(POSITIONS_FILE, "r") as f:
            return json.load(f)
    except:
        return []


def save_positions(positions):
    with open(POSITIONS_FILE, "w") as f:
        json.dump(positions, f, indent=4)


# =========================
# CONTROL
# =========================
def can_open_new_position():
    positions = load_positions()
    return len(positions) < MAX_POSITIONS


# =========================
# ADD POSITION
# =========================
def add_position(symbol, price, quantity, capital=0):

    positions = load_positions()

    position = {
        "symbol": symbol,
        "entry_price": price,
        "quantity": quantity,
        "capital": capital
    }

    positions.append(position)
    save_positions(positions)

    print(f"✅ Posición abierta: {symbol} | price: {price} | qty: {quantity}")


# =========================
# GET POSITIONS
# =========================
def get_open_positions():
    return load_positions()


# =========================
# CLOSE POSITION
# =========================
def close_position(symbol, price):

    positions = load_positions()

    for pos in positions:

        if pos["symbol"] == symbol:

            entry = float(pos["entry_price"])
            qty = float(pos["quantity"])
            capital = float(pos.get("capital", entry * qty))

            pnl = (price - entry) * qty

            print(f"💰 Cerrada {symbol} | PnL: {pnl}")

            positions.remove(pos)
            save_positions(positions)

            return pnl  # 🔥 importante devolver PnL

    return 0