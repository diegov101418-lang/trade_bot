def get_alerts(running, stats, performance, portfolio):
    alerts = []

    risk_pct = float(portfolio.get("risk_pct", 0))
    floating_pnl = float(portfolio.get("floating_pnl", 0))
    open_positions = int(portfolio.get("open_positions_count", 0))

    winrate = float(stats.get("winrate", 0))
    total_trades = int(stats.get("total", 0))

    net_profit = float(
        performance.get(
            "net_profit",
            float(performance.get("profit", 0)) + float(performance.get("loss", 0))
        )
    )

    if risk_pct >= 50:
        alerts.append("⛔ Riesgo alto: exposición superior al 50%")
    elif risk_pct >= 20:
        alerts.append("⚠ Riesgo moderado: exposición entre 20% y 50%")

    if open_positions >= 3:
        alerts.append(f"📂 Varias posiciones abiertas: {open_positions}")

    if floating_pnl < 0:
        alerts.append(f"📉 PnL flotante negativo: {floating_pnl:.4f}")
    elif floating_pnl > 0:
        alerts.append(f"📈 PnL flotante positivo: {floating_pnl:.4f}")

    if total_trades > 30 and winrate < 40:
        alerts.append(f"⚠ Winrate bajo: {winrate:.2f}%")

    if net_profit > 0:
        alerts.append(f"✅ Sistema en ganancia neta: {net_profit:.4f}")
    elif net_profit < 0:
        alerts.append(f"⚠ Sistema en pérdida neta: {net_profit:.4f}")

    if not running:
        alerts.append("⏸ Bot en pausa")

    return alerts