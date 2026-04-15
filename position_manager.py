import json
import os
import time
from config import MAX_POSITIONS

POSITIONS_FILE = "positions.json"


# =========================
# LOAD / SAVE
# =========================
def load_positions():
    if not os.path.exists(POSITIONS_FILE):
        return []

    try:
        with open(POSITIONS_FILE, "r", encoding="utf-8") as f:
            positions = json.load(f)

            for p in positions:
                if "take_profit" not in p:
                    p["take_profit"] = None
                if "stop_loss" not in p:
                    p["stop_loss"] = None
                if "max_price" not in p:
                    p["max_price"] = p.get("entry_price", 0)
                if "min_price" not in p:
                    p["min_price"] = p.get("entry_price", 0)
                if "partial_tp_done" not in p:
                    p["partial_tp_done"] = False
                if "open_time" not in p:
                    p["open_time"] = None
                if "strategy_name" not in p:
                    p["strategy_name"] = ""
                if "tp_pct" not in p:
                    p["tp_pct"] = None

            return positions

    except Exception:
        return []


def save_positions(positions):
    with open(POSITIONS_FILE, "w", encoding="utf-8") as f:
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
def add_position(
    symbol,
    price,
    quantity,
    capital=0,
    stop_loss=None,
    take_profit=None,
    extra=None
):
    positions = load_positions()
    extra = extra or {}

    position = {
        "symbol": symbol,
        "entry_price": price,
        "quantity": quantity,
        "capital": capital,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "max_price": price,
        "min_price": price,
        "partial_tp_done": bool(extra.get("partial_tp_done", False)),
        "open_time": extra.get("open_time", time.time()),
        "strategy_name": extra.get("strategy_name", ""),
        "tp_pct": extra.get("tp_pct"),
    }

    positions.append(position)
    save_positions(positions)

    print(f"✅ Posición abierta: {symbol} | price: {price} | qty: {quantity}")


# =========================
# UPDATE EXTREMES
# =========================
def update_position_extremes(symbol, price):
    positions = load_positions()
    updated = False

    for pos in positions:
        if pos.get("symbol") == symbol:
            entry_price = float(pos.get("entry_price", price))
            current_max = float(pos.get("max_price", entry_price))
            current_min = float(pos.get("min_price", entry_price))

            if price > current_max:
                pos["max_price"] = price

            if price < current_min:
                pos["min_price"] = price

            updated = True
            break

    if updated:
        save_positions(positions)

    return updated


# =========================
# GET POSITIONS
# =========================
def get_open_positions():
    return load_positions()


# =========================
# GET SINGLE POSITION
# =========================
def get_position(symbol):
    positions = load_positions()

    for pos in positions:
        if pos.get("symbol") == symbol:
            return pos

    return None


# =========================
# MARK PARTIAL TP
# =========================
def mark_partial_tp_done(symbol, done=True):
    positions = load_positions()
    updated = False

    for pos in positions:
        if pos.get("symbol") == symbol:
            pos["partial_tp_done"] = bool(done)
            updated = True
            break

    if updated:
        save_positions(positions)

    return updated


# =========================
# REDUCE POSITION
# =========================
def reduce_position(symbol, reduce_qty, price):
    positions = load_positions()

    for pos in positions:
        if pos.get("symbol") == symbol:
            entry = float(pos["entry_price"])
            qty = float(pos["quantity"])
            capital = float(pos.get("capital", entry * qty))
            reduce_qty = float(reduce_qty)

            if reduce_qty <= 0 or qty <= 0:
                return 0

            if reduce_qty >= qty:
                reduce_qty = qty

            pnl_partial = (price - entry) * reduce_qty

            remaining_qty = qty - reduce_qty
            qty_ratio = remaining_qty / qty if qty > 0 else 0
            remaining_capital = capital * qty_ratio

            pos["quantity"] = remaining_qty
            pos["capital"] = remaining_capital
            pos["partial_tp_done"] = True

            if remaining_qty <= 0.00000001:
                positions.remove(pos)
            else:
                # mantener max/min/open_time/tp_pct/strategy_name intactos
                pass

            save_positions(positions)

            print(
                f"💰 Parcial {symbol} | "
                f"reduce_qty={reduce_qty} | "
                f"remaining_qty={remaining_qty} | "
                f"pnl_partial={pnl_partial}"
            )

            return pnl_partial

    return 0


# =========================
# CLOSE POSITION
# =========================
def close_position(symbol, price):
    positions = load_positions()

    for pos in positions:
        if pos.get("symbol") == symbol:
            entry = float(pos["entry_price"])
            qty = float(pos["quantity"])
            capital = float(pos.get("capital", entry * qty))

            pnl = (price - entry) * qty

            stop = pos.get("stop_loss")
            tp = pos.get("take_profit")

            rr = None
            if stop and tp and entry:
                risk = abs(entry - float(stop))
                reward = abs(float(tp) - entry)
                if risk > 0:
                    rr = reward / risk

            print(f"💰 Cerrada {symbol} | PnL: {pnl} | RR: {rr}")

            positions.remove(pos)
            save_positions(positions)

            return pnl

    return 0