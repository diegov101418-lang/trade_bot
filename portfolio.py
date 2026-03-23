import json
import os

FILE = "portfolio.json"
INITIAL_BALANCE = 1000


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
        json.dump(data, f, indent=4)


def get_balance():
    return load()["balance_total"]


def get_free_balance():
    return load()["balance_free"]


def get_used_balance():
    return load()["balance_used"]


def get_equity():
    data = load()
    return data["balance_total"] + data["pnl_unrealized"]


def lock_balance(amount):
    if amount <= 0:
        print("❌ Amount inválido")
        return False

    data = load()

    if data["balance_free"] < amount:
        print(f"❌ No hay balance suficiente | libre: {data['balance_free']}")
        return False

    data["balance_free"] -= amount
    data["balance_used"] += amount

    save(data)
    print(f"🔒 Bloqueado: {amount}")
    return True


def unlock_balance(amount, pnl):
    data = load()

    data["balance_used"] -= amount
    data["balance_free"] += amount
    data["balance_total"] += pnl

    if data["balance_used"] < 0:
        data["balance_used"] = 0

    save(data)
    print(f"🔓 Liberado: {amount} | PnL: {pnl}")