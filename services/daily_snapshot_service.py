import json
import os
import time
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from config import get_mode, get_strategy_name, is_running
from services.positions_service import get_live_positions
from services.portfolio_service import get_portfolio_data
from services.daily_stats_service import get_today_stats

OUTPUT_FILE = "daily_snapshots.json"
MAX_SNAPSHOTS = 365  # Mantener último año

logger = logging.getLogger(__name__)


def safe_float(value: Any, default: float = 0.0, decimals: int = 4) -> float:
    """Convierte un valor a float de forma segura."""
    try:
        if value is None:
            return default
        return round(float(value), decimals)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """Convierte un valor a int de forma segura."""
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_str(value: Any, default: str = "-") -> str:
    """Convierte un valor a string de forma segura."""
    try:
        if value is None:
            return default
        text = str(value).strip()
        return text if text else default
    except Exception:
        return default


def load_daily_snapshots(output_file: str = OUTPUT_FILE) -> List[Dict[str, Any]]:
    """Carga snapshots desde archivo JSON."""
    if not os.path.exists(output_file):
        return []

    try:
        with open(output_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                logger.warning("Formato inválido en %s, se devuelve lista vacía", output_file)
                return []
            return data
    except json.JSONDecodeError as e:
        logger.error("JSON corrupto en %s: %s", output_file, e)
        return []
    except Exception as e:
        logger.error("Error leyendo %s: %s", output_file, e)
        return []


def save_daily_snapshots(data: List[Dict[str, Any]], output_file: str = OUTPUT_FILE) -> bool:
    """Guarda snapshots de forma atómica para evitar corrupción."""
    temp_file = output_file + ".tmp"

    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        os.replace(temp_file, output_file)
        return True

    except Exception as e:
        logger.error("Error guardando %s: %s", output_file, e)

        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception:
                pass

        return False


def build_today_snapshot() -> Dict[str, Any]:
    """Construye el snapshot del día actual."""
    try:
        live_positions = get_live_positions()
        portfolio = get_portfolio_data(live_positions)
        today_stats = get_today_stats()
    except Exception as e:
        logger.error("Error obteniendo datos de servicios: %s", e)
        live_positions = []
        portfolio = {}
        today_stats = {}

    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    open_symbols = []
    for pos in live_positions:
        if isinstance(pos, dict):
            symbol = safe_str(pos.get("symbol"), "")
            if symbol:
                open_symbols.append(symbol)

    traded_symbols = today_stats.get("symbols", [])
    if not isinstance(traded_symbols, list):
        traded_symbols = []

    snapshot = {
        "date": today_str,
        "timestamp": int(time.time()),

        # estado de cuenta
        "balance": safe_float(portfolio.get("balance"), 0),
        "equity": safe_float(portfolio.get("equity"), 0),
        "free_balance": safe_float(portfolio.get("free_balance"), 0),
        "used_balance": safe_float(portfolio.get("used_balance"), 0),
        "floating_pnl": safe_float(portfolio.get("floating_pnl"), 0),
        "risk_pct": safe_float(portfolio.get("risk_pct"), 0, decimals=2),
        "open_positions_count": safe_int(portfolio.get("open_positions_count"), 0),

        # contexto del bot
        "bot_running": bool(is_running()),
        "mode": safe_str(get_mode()),
        "strategy": safe_str(get_strategy_name()),

        # resumen del día
        "daily_trades": safe_int(today_stats.get("trades"), 0),
        "daily_wins": safe_int(today_stats.get("wins"), 0),
        "daily_losses": safe_int(today_stats.get("losses"), 0),
        "daily_breakeven": safe_int(today_stats.get("breakeven"), 0),
        "daily_winrate": safe_float(today_stats.get("winrate"), 0, decimals=2),
        "daily_pnl_gross": safe_float(today_stats.get("pnl_gross"), 0),
        "daily_pnl_net": safe_float(today_stats.get("pnl_net"), 0),
        "daily_fees": safe_float(today_stats.get("fees"), 0),
        "daily_avg_trade": safe_float(today_stats.get("avg_trade"), 0),
        "daily_best_trade": safe_float(today_stats.get("best_trade"), 0),
        "daily_worst_trade": safe_float(today_stats.get("worst_trade"), 0),

        # símbolos
        "symbols_traded": traded_symbols,
        "open_symbols": sorted(set(open_symbols)),
    }

    return snapshot


def upsert_today_snapshot(output_file: str = OUTPUT_FILE) -> Optional[Dict[str, Any]]:
    """
    Inserta o actualiza el snapshot de hoy.
    Mantiene un máximo de MAX_SNAPSHOTS registros.
    """
    data = load_daily_snapshots(output_file)
    snapshot = build_today_snapshot()
    today_str = snapshot["date"]

    updated = False

    for i, item in enumerate(data):
        if isinstance(item, dict) and item.get("date") == today_str:
            data[i] = snapshot
            updated = True
            logger.info("Snapshot actualizado para %s", today_str)
            break

    if not updated:
        data.append(snapshot)
        logger.info("Nuevo snapshot creado para %s", today_str)

    data.sort(key=lambda x: x.get("date", ""), reverse=True)

    if len(data) > MAX_SNAPSHOTS:
        removed = len(data) - MAX_SNAPSHOTS
        data = data[:MAX_SNAPSHOTS]
        logger.info("Eliminados %s snapshots antiguos (límite: %s)", removed, MAX_SNAPSHOTS)

    return snapshot if save_daily_snapshots(data, output_file) else None


def get_today_snapshot(output_file: str = OUTPUT_FILE) -> Dict[str, Any]:
    """Obtiene el snapshot de hoy desde archivo o lo construye en vivo si no existe."""
    data = load_daily_snapshots(output_file)
    today_str = datetime.now().strftime("%Y-%m-%d")

    for item in data:
        if isinstance(item, dict) and item.get("date") == today_str:
            return item

    return build_today_snapshot()


def get_snapshot_by_date(date_str: str, output_file: str = OUTPUT_FILE) -> Optional[Dict[str, Any]]:
    """Obtiene el snapshot de una fecha específica (YYYY-MM-DD)."""
    data = load_daily_snapshots(output_file)

    for item in data:
        if isinstance(item, dict) and item.get("date") == date_str:
            return item

    return None


def get_latest_snapshots(n: int = 7, output_file: str = OUTPUT_FILE) -> List[Dict[str, Any]]:
    """Obtiene los últimos N snapshots."""
    data = load_daily_snapshots(output_file)
    return data[:max(0, n)]


def get_snapshots_range(start_date: str, end_date: str, output_file: str = OUTPUT_FILE) -> List[Dict[str, Any]]:
    """Obtiene snapshots dentro de un rango de fechas YYYY-MM-DD."""
    data = load_daily_snapshots(output_file)

    result = []
    for item in data:
        date = item.get("date", "")
        if start_date <= date <= end_date:
            result.append(item)

    return result


if __name__ == "__main__":
    snapshot = upsert_today_snapshot()
    if snapshot:
        print("\n✅ Snapshot guardado:")
        print(f"   Fecha: {snapshot['date']}")
        print(f"   Balance: {snapshot['balance']}")
        print(f"   Equity: {snapshot['equity']}")
        print(f"   P&L Net día: {snapshot['daily_pnl_net']}")
        print(f"   Winrate día: {snapshot['daily_winrate']}%")