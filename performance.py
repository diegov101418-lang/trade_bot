from portfolio import get_balance
from config import RISK_PER_TRADE
import csv
import os

TRADES_FILE = "trades_dataset.csv"

def get_performance():
    """
    Calcula la performance del bot:
    - balance actual
    - historial del balance
    - ganancias y pérdidas totales
    - winrate
    """
    balance = 1000  # saldo inicial
    history = []
    total_profit = 0
    total_loss = 0
    wins = 0
    losses = 0
    trades_count = 0

    if not os.path.exists(TRADES_FILE):
        return {
            "balance": balance,
            "history": history,
            "profit": total_profit,
            "loss": total_loss,
            "wins": wins,
            "losses": losses,
            "winrate": 0,
            "trades": trades_count
        }

    with open(TRADES_FILE, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            trades_count += 1
            result = float(row.get("result", 0))  # resultado de la operación
            balance += result
            history.append(balance)

            if result > 0:
                total_profit += result
                wins += 1
            elif result < 0:
                total_loss += result
                losses += 1

    total_trades = wins + losses
    winrate = round((wins / total_trades) * 100, 2) if total_trades > 0 else 0

    return {
        "balance": round(balance, 2),
        "history": history,
        "profit": round(total_profit, 2),
        "loss": round(total_loss, 2),
        "wins": wins,
        "losses": losses,
        "winrate": winrate,
        "trades": trades_count
    }

def calculate_quantity(price):
    """
    Calcula la cantidad a comprar según balance y riesgo.
    price: precio actual de la moneda
    """
    if price is None or price <= 0:
        return 0

    balance = get_balance()  # balance actual
    risk_amount = balance * RISK_PER_TRADE

    quantity = risk_amount / price

    # opcional: redondear a 6 decimales para evitar problemas de exchange
    quantity = round(quantity, 6)

    return quantity


# Ejemplo de uso:
price = 0.04546  # reemplazar con el precio actual de la moneda
quantity = calculate_quantity(price)
print("Cantidad a abrir:", quantity)