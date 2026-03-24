import csv
import os
from portfolio import get_balance

TRADES_FILE = "trades_dataset.csv"
INITIAL_BALANCE = 1000


def get_performance():
    real_balance = get_balance()
    history = []

    total_profit = 0
    total_loss = 0
    wins = 0
    losses = 0
    trades_count = 0

    running_balance = INITIAL_BALANCE
    peak_balance = INITIAL_BALANCE
    max_drawdown = 0

    if not os.path.exists(TRADES_FILE):
        return build_response(
            real_balance,
            history,
            total_profit,
            total_loss,
            wins,
            losses,
            trades_count,
            max_drawdown
        )

    with open(TRADES_FILE, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            raw_result = row.get("result", "")
            raw_pnl = row.get("pnl", "")

            # ignorar trades sin cerrar
            if raw_result == "":
                continue

            trades_count += 1

            try:
                result = int(float(raw_result))
            except:
                continue

            if result == 1:
                wins += 1
            else:
                losses += 1

            pnl_value = 0
            if raw_pnl != "":
                try:
                    pnl_value = float(raw_pnl)
                except:
                    pnl_value = 0

            if pnl_value > 0:
                total_profit += pnl_value
            elif pnl_value < 0:
                total_loss += pnl_value

            running_balance += pnl_value
            history.append(round(running_balance, 2))

            if running_balance > peak_balance:
                peak_balance = running_balance

            if peak_balance > 0:
                dd = ((running_balance - peak_balance) / peak_balance) * 100
                if dd < max_drawdown:
                    max_drawdown = dd

    return build_response(
        real_balance,
        history,
        total_profit,
        total_loss,
        wins,
        losses,
        trades_count,
        max_drawdown
    )


def build_response(balance, history, profit, loss, wins, losses, trades, max_drawdown):
    total_trades = wins + losses
    winrate = round((wins / total_trades) * 100, 2) if total_trades > 0 else 0

    net_profit = profit + loss
    avg_profit_per_trade = net_profit / trades if trades > 0 else 0

    return {
        "balance": round(balance, 2),
        "history": history[-100:],
        "profit": round(profit, 2),
        "loss": round(loss, 2),
        "net_profit": round(net_profit, 2),
        "avg_profit_per_trade": round(avg_profit_per_trade, 2),
        "wins": wins,
        "losses": losses,
        "winrate": winrate,
        "trades": trades,
        "max_drawdown": round(max_drawdown, 2)
    }