import json
import os

FILE = "portfolio.json"

INITIAL_BALANCE = 1000


# =========================
# INIT
# =========================
def load():

    if not os.path.exists(FILE):
        data = {
            "balance_total": INITIAL_BALANCE,
            "balance_free": INITIAL_BALANCE,
            "balance_used": 0,
            "pnl_unrealized": 0
        }
        save(data)
        return data

    try:
        with open(FILE, "r") as f:
            return json.load(f)
    except:
        return {
            "balance_total": INITIAL_BALANCE,
            "balance_free": INITIAL_BALANCE,
            "balance_used": 0,
            "pnl_unrealized": 0
        }


def save(data):

    with open(FILE, "w") as f:
        json.dump(data, f)


# =========================
# GETTERS
# =========================
def get_balance():
    return load()["balance_total"]

def get_free_balance():
    return load()["balance_free"]

def get_used_balance():
    return load()["balance_used"]

def get_equity():
    data = load()
    return data["balance_total"] + data["pnl_unrealized"]


# =========================
# ABRIR POSICIÓN
# =========================
def lock_balance(amount):

    data = load()

    if data["balance_free"] < amount:
        return False

    data["balance_free"] -= amount
    data["balance_used"] += amount

    save(data)
    return True


# =========================
# CERRAR POSICIÓN
# =========================
def unlock_balance(amount, pnl):

    data = load()

    data["balance_used"] -= amount
    data["balance_free"] += amount

    # aplicar ganancia/pérdida
    data["balance_total"] += pnl

    save(data)


# =========================
# ACTUALIZAR PNL FLOTANTE
# =========================
def update_unrealized_pnl(pnl):

    data = load()
    data["pnl_unrealized"] = pnl
    save(data)