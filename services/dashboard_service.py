import json
import os
import time
from datetime import datetime

from config import is_running, get_mode, get_strategy_name
from performance import get_performance

from services.trades_service import get_trades, get_stats
from services.positions_service import get_live_positions
from services.portfolio_service import get_portfolio_data, get_risk_metrics
from services.alerts_service import get_alerts
from ai_strategy_learner import suggest_context_decision
from indicators import get_indicators


BOT_VERSION = "v2.0"
MAX_TRADES_PER_DAY = 30
DECISION_FILE = "last_decisions.json"
MAX_DECISIONS = 50


# =========================
# DECISIONES RECIENTES (archivo json)
# =========================
def add_last_decision(symbol, decision, confidence, liquidity, reason):
    try:
        item = {
            "symbol": str(symbol or "-"),
            "decision": str(decision or "SKIP"),
            "confidence": round(float(confidence or 0), 2),
            "liquidity": str(liquidity or "-"),
            "reason": str(reason or "-"),
            "time": time.time(),
        }
    except Exception:
        item = {
            "symbol": str(symbol or "-"),
            "decision": str(decision or "SKIP"),
            "confidence": 0.0,
            "liquidity": str(liquidity or "-"),
            "reason": str(reason or "-"),
            "time": time.time(),
        }

    try:
        if os.path.exists(DECISION_FILE):
            with open(DECISION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = []

        data.insert(0, item)
        data = data[:MAX_DECISIONS]

        with open(DECISION_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"❌ Error guardando decision IA: {e}")


def get_last_decisions():
    try:
        if os.path.exists(DECISION_FILE):
            with open(DECISION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
    except Exception as e:
        print(f"❌ Error leyendo decisiones IA: {e}")

    return []


def clear_last_decisions():
    try:
        with open(DECISION_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
    except Exception as e:
        print(f"❌ Error limpiando decisiones IA: {e}")


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

    ai_data = {
        "strategy_suggestion": None,
        "risk_suggestion": None,
    }

    try:
        df = get_indicators("BTCUSDT")
        if df is not None and len(df) > 0:
            last = df.iloc[-1]

            price = float(last["close"])
            ma50 = float(last["ma50"])
            atr = float(last["atr"])
            volume = float(last["volume"])
            avg_volume = float(df["volume"].mean())
            vol_ratio = volume / avg_volume if avg_volume > 0 else 1
            atr_pct = (atr / price) * 100 if price > 0 else 0

            if price > ma50:
                market_regime = "bull"
            elif price < ma50:
                market_regime = "bear"
            else:
                market_regime = "sideways"

            if atr_pct < 1.0:
                volatility_context = "low"
            elif atr_pct < 2.5:
                volatility_context = "medium"
            else:
                volatility_context = "high"

            now_dt = datetime.now()

            ai_data = suggest_context_decision({
                "rsi": float(last.get("rsi", 50)),
                "volume": vol_ratio,
                "trend": int(price > ma50),
                "momentum": price - ma50,
                "hour": now_dt.hour,
                "day_of_week": now_dt.weekday(),
                "signal_confidence": 0.7,
                "market_regime": market_regime,
                "atr": atr,
                "volatility_context": volatility_context,
            })
    except Exception as e:
        print(f"⚠ Error IA dashboard: {e}")

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
        "ai": ai_data,
        "last_decisions": get_last_decisions(),
    }