from portfolio import get_balance, get_free_balance, get_used_balance


def get_portfolio_data(live_positions=None):
    if live_positions is None:
        live_positions = []

    balance = float(get_balance() or 0)
    free_balance = float(get_free_balance() or 0)
    used_balance = float(get_used_balance() or 0)

    floating_pnl = round(sum(float(p.get("pnl", 0) or 0) for p in live_positions), 4)
    equity = round(balance + floating_pnl, 4)
    risk_pct = round((used_balance / balance) * 100, 2) if balance > 0 else 0
    open_positions_count = len(live_positions)

    return {
        "balance": round(balance, 4),
        "free_balance": round(free_balance, 4),
        "used_balance": round(used_balance, 4),
        "equity": equity,
        "floating_pnl": floating_pnl,
        "risk_pct": risk_pct,   # exposición actual
        "open_positions_count": open_positions_count,
    }


def get_risk_metrics(live_positions=None):
    if live_positions is None:
        live_positions = []

    balance = float(get_balance() or 0)

    total_open_risk = 0.0
    positions_with_stop = 0

    for pos in live_positions:
        try:
            entry = float(pos.get("entry_price", 0) or 0)
            qty = float(pos.get("quantity", 0) or 0)

            stop_loss = pos.get("stop_loss", None)
            if stop_loss in (None, "", "None"):
                continue

            stop_loss = float(stop_loss)

            risk_amount = abs(entry - stop_loss) * qty
            total_open_risk += risk_amount
            positions_with_stop += 1

        except Exception as e:
            print(f"⚠ Error calculando riesgo para {pos.get('symbol')}: {e}")
            continue

    avg_risk_per_trade = (
        total_open_risk / positions_with_stop
        if positions_with_stop > 0 else 0
    )

    risk_pct_real = (
        (total_open_risk / balance) * 100
        if balance > 0 else 0
    )

    return {
        "total_open_risk": round(total_open_risk, 4),
        "avg_risk_per_trade": round(avg_risk_per_trade, 4),
        "risk_pct_real": round(risk_pct_real, 2),
        "positions_with_stop": positions_with_stop,
    }