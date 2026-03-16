import csv

def get_performance():

    profit = 0
    loss = 0
    total = 0

    history = []

    try:

        with open("trades_dataset.csv", "r") as f:

            reader = csv.DictReader(f)

            balance = 0

            for row in reader:

                pnl = float(row.get("pnl", 0))

                balance += pnl

                history.append(balance)

                if pnl > 0:
                    profit += pnl
                else:
                    loss += pnl

                total += pnl

    except:
        pass

    return {
        "profit": round(profit,2),
        "loss": round(loss,2),
        "total": round(total,2),
        "history": history[-50:]
    }