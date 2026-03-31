import time

from config import is_running, get_mode, get_strategy_name
from performance import get_performance

from services.trades_service import get_trades, get_stats
from services.positions_service import get_live_positions
from services.portfolio_service import get_portfolio_data, get_risk_metrics
from services.alerts_service import get_alerts


BOT_VERSION = "v2.0"
MAX_TRADES_PER_DAY = 30


def get_dashboard_data():
    live_positions = get_live_positions()
    trades = get_trades()
    stats = get_stats()
    performance = get_performance()
    portfolio = get_portfolio_data(live_positions)
    running = is_running()
    risk_data = get_risk_metrics(live_positions)

    alerts = get_alerts(
        running=running,
        stats=stats,
        performance=performance,
        portfolio=portfolio,
    )

    return {
        "positions": live_positions,
        "trades": trades,

        "balance": portfolio["balance"],
        "free_balance": portfolio["free_balance"],
        "used_balance": portfolio["used_balance"],
        "equity": portfolio["equity"],
        "floating_pnl": portfolio["floating_pnl"],
        "risk_pct": portfolio["risk_pct"],
        "open_positions_count": portfolio["open_positions_count"],
        "risk_metrics": risk_data,

        "performance": performance,
        "history": performance.get("history", []),
        "stats": stats,

        "mode": get_mode(),
        "running": running,
        "strategy": get_strategy_name(),
        "time": time.time(),

        "version": BOT_VERSION,
        "daily_trades": min(int(performance.get("trades", 0)), MAX_TRADES_PER_DAY),
        "max_trades_per_day": MAX_TRADES_PER_DAY,

        "alerts": alerts,
    }