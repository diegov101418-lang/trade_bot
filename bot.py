import time
import holidays
import re
from datetime import datetime, timezone, timedelta, date

from risk_manager import (
    check_limits,
    register_trade,
    get_winrate,
    get_total_closed_trades,
    update_trade_result,
    calculate_position_size,
    ensure_trades_file,
)
from indicators import get_indicators
from scanner import scan_market
from market_ranker import rank_symbols
from ai_model import predict_trade
from strategy_manager import evaluate_strategies
from position_manager import (
    add_position,
    close_position,
    get_open_positions,
    update_position_extremes,
    reduce_position,
    get_position,
)
from symbol_filter import symbol_is_blocked

from config import (
    is_running,
    load_best_config,
    RISK_PER_TRADE,
    MAX_POSITIONS,
    get_mode,
    get_strategy_name,
)

from portfolio import get_balance, get_free_balance, lock_balance, unlock_balance
from executor import buy, sell
from ai_auto_trainer import maybe_retrain
from ai_strategy_learner import suggest_context_decision
from services.dashboard_service import add_last_decision
from logger import log, log_order


# =========================
# HOLIDAYS
# =========================
us_holidays = holidays.US()
ar_holidays = holidays.Argentina()
uk_holidays = holidays.UK()
de_holidays = holidays.Germany()
jp_holidays = holidays.Japan()
cn_holidays = holidays.China()
kr_holidays = holidays.SouthKorea()


def get_easter_sunday(year: int) -> date:
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def get_good_friday(year: int) -> date:
    return get_easter_sunday(year) - timedelta(days=2)


# =========================
# SESSION
# =========================
def get_market_session(hour_utc: int) -> str:
    if 0 <= hour_utc < 8:
        return "asia"
    elif 8 <= hour_utc < 13:
        return "europe"
    elif 13 <= hour_utc < 21:
        return "us"
    return "off"


# =========================
# SYMBOL FILTER
# =========================
def is_valid_trade_symbol(symbol: str) -> bool:
    if not symbol:
        return False

    symbol = str(symbol).upper().strip()

    if not symbol.endswith("USDT"):
        return False

    if not re.fullmatch(r"[A-Z0-9]+USDT", symbol):
        return False

    blocked_symbols = {
        "USDTRUB",
        "USDTIDRT",
        "USDCUSDT",
        "BUSDUSDT",
        "TUSDUSDT",
        "FDUSDUSDT",
        "USDPUSDT",
        "EURUSDT",
        "TRYUSDT",
        "BRLUSDT",
        "RUBUSDT",
        "IDRTUSDT",
        "DAIUSDT",
    }

    if symbol in blocked_symbols:
        return False

    base = symbol[:-4]

    blocked_bases = {
        "USDT",
        "USDC",
        "BUSD",
        "TUSD",
        "FDUSD",
        "USDP",
        "DAI",
        "EUR",
        "TRY",
        "BRL",
        "RUB",
        "IDRT",
    }

    if base in blocked_bases:
        return False

    return True


# =========================
# LIQUIDITY + AI FILTER
# =========================
def get_holiday_flags(today):
    return {
        "is_holiday_us": int(today in us_holidays),
        "is_holiday_ar": int(today in ar_holidays),
        "is_holiday_eu": int((today in uk_holidays) or (today in de_holidays)),
        "is_holiday_asia": int(
            (today in jp_holidays) or
            (today in cn_holidays) or
            (today in kr_holidays)
        ),
        "is_good_friday": int(today == get_good_friday(today.year)),
    }


def get_liquidity_mode(avg_dollar_volume, market_session, holiday_flags):
    holiday_score = (
        holiday_flags["is_holiday_us"] +
        holiday_flags["is_holiday_eu"] +
        holiday_flags["is_holiday_asia"] +
        holiday_flags["is_good_friday"]
    )

    print(
        f"DEBUG liquidity | "
        f"avg_$vol={avg_dollar_volume:.2f} | "
        f"session={market_session} | "
        f"holiday_score={holiday_score} | "
        f"flags={holiday_flags}"
    )

    if avg_dollar_volume < 50000:
        return "low"

    if market_session == "off" and avg_dollar_volume < 100000:
        return "low"

    if holiday_score >= 2 and avg_dollar_volume < 250000:
        return "low"

    if holiday_score >= 1 or market_session == "off":
        return "medium"

    return "normal"


def evaluate_trade_context(
    liquidity_mode,
    signal_confidence,
    market_regime,
    ai_decision,
    ia_risk,
    system_winrate,
    total_closed_trades,
    recovery,
    trend_change,
    bearish_rebound,
):
    allow_trade = True
    risk_mode_final = "normal"
    reason = "ok"

    if liquidity_mode == "low":
        allow_trade = False
        reason = "low_liquidity"

    elif liquidity_mode == "medium":
        if signal_confidence < 0.78 and market_regime != "bull":
            allow_trade = False
            reason = "medium_liquidity_low_confidence"

    if ai_decision == 0:
        if liquidity_mode in ["low", "medium"] or signal_confidence < 0.80:
            allow_trade = False
            reason = "ai_blocked_trade"

    exceptional_setup = recovery or trend_change or bearish_rebound

    if exceptional_setup and signal_confidence >= 0.82 and market_regime == "bull":
        if liquidity_mode == "medium":
            allow_trade = True
            reason = "exceptional_setup_override"

    if total_closed_trades >= 20 and system_winrate is not None:
        if system_winrate < 0.35 and signal_confidence < 0.78:
            allow_trade = False
            reason = "low_system_winrate"

    if signal_confidence >= 0.85 and market_regime == "bull":
        risk_mode_final = "aggressive"
    elif signal_confidence < 0.72 or liquidity_mode != "normal":
        risk_mode_final = "conservative"
    else:
        risk_mode_final = "normal"

    ia_risk = str(ia_risk or "").lower().strip()

    if ia_risk in ["aggressive", "normal", "conservative"]:
        if liquidity_mode == "low":
            risk_mode_final = "conservative"
        elif liquidity_mode == "medium" and ia_risk == "aggressive":
            risk_mode_final = "normal"
        else:
            risk_mode_final = ia_risk

    if not allow_trade:
        risk_mode_final = "conservative"

    return {
        "allow_trade": allow_trade,
        "risk_mode_final": risk_mode_final,
        "reason": reason,
    }


# =========================
# TRAILING + CONTROL
# =========================
trailing_data = {}
last_trade_time = {}
open_time_data = {}


def update_trailing(symbol, price, atr, volatility_context, entry_price):
    if symbol not in trailing_data:
        trailing_data[symbol] = {"max_price": price}

    if price > trailing_data[symbol]["max_price"]:
        trailing_data[symbol]["max_price"] = price

    max_price = trailing_data[symbol]["max_price"]
    profit_pct = (price - entry_price) / entry_price

    # no activar trailing hasta +2%
    if profit_pct < 0.02:
        return False

    if volatility_context == "low":
        multiplier = 1.8
    elif volatility_context == "medium":
        multiplier = 2.2
    else:
        multiplier = 2.8

    trailing_stop = max_price - (atr * multiplier)
    return price < trailing_stop


def should_close_by_time(symbol, pos, price):
    open_time = pos.get("open_time") or open_time_data.get(symbol)
    if not open_time:
        return False, ""

    minutes_open = (time.time() - float(open_time)) / 60.0
    entry = float(pos["entry_price"])
    profit_pct = (price - entry) / entry if entry > 0 else 0

    if minutes_open > 90 and profit_pct < 0.015:
        return True, "timeout_weak"

    if minutes_open > 180:
        return True, "timeout_max"

    return False, ""


def can_trade(symbol):
    now = time.time()

    if symbol in last_trade_time and now - last_trade_time[symbol] < 180:
        return False

    last_trade_time[symbol] = now
    return True


# =========================
# CONFIG DINÁMICA
# =========================
def get_strategy():
    best = load_best_config()

    if best:
        return best["rsi"], best["tp"], best["sl"]

    return 35, 0.08, -0.02


def get_required_confidence(strategy_name):
    strategy_name = str(strategy_name or "").strip().lower()

    if strategy_name == "mean_reversion":
        return 0.78
    if strategy_name == "breakout":
        return 0.72
    if strategy_name == "trend":
        return 0.70

    return 0.72


def get_dynamic_tp(strategy_name, volatility_context, base_tp, signal_confidence):
    strategy_name = str(strategy_name or "").strip().lower()

    if strategy_name == "mean_reversion":
        tp_pct = 0.045
    elif strategy_name == "trend":
        tp_pct = 0.075
    elif strategy_name == "breakout":
        tp_pct = 0.09
    else:
        tp_pct = base_tp

    if volatility_context == "low":
        tp_pct *= 0.85
    elif volatility_context == "high":
        tp_pct *= 1.15

    confidence_boost = 1 + max(0, min(0.15, signal_confidence - 0.70))
    return tp_pct * confidence_boost


def get_partial_tp_trigger(tp_pct):
    if tp_pct <= 0.05:
        return 0.02
    elif tp_pct <= 0.08:
        return 0.03
    return 0.035


# =========================
# AYUDA IA: elegir señal
# =========================
def choose_signal_with_ai(signals, ai_strategy_name):
    if not signals:
        return None

    strategy_target = str(ai_strategy_name or "").strip().lower()

    if strategy_target:
        for s in signals:
            s_name = str(s.get("strategy", "")).strip().lower()
            if s_name == strategy_target:
                return s

    return max(signals, key=lambda x: float(x.get("confidence", 0)))


# =========================
# PROCESAR MONEDA
# =========================
def process_symbol(symbol):
    log(f"Entrando a process_symbol: {symbol}")

    try:
        df = get_indicators(symbol)

        if df is None or len(df) < 50:
            log(f"⚠ {symbol} sin datos suficientes")
            add_last_decision(symbol, "SKIP", 0, "-", "insufficient_data")
            return

        last = df.iloc[-1]

        price = float(last["close"])
        rsi = float(last["rsi"])
        ma50 = float(last["ma50"])
        ma200 = float(last["ma200"])
        volume = float(last["volume"])
        avg_volume = float(df["volume"].mean())
        avg_dollar_volume = avg_volume * price
        atr = float(last["atr"])

    except Exception as e:
        log(f"❌ Error datos {symbol}: {e}")
        add_last_decision(symbol, "SKIP", 0, "-", "indicator_error")
        return

    _, BEST_TP, BEST_SL = get_strategy()

    positions = get_open_positions()
    symbols_open = [p["symbol"] for p in positions]
    mode = get_mode()

    bearish = ma50 < ma200 and price < ma50

    if ma50 > ma200 and price > ma50:
        market_regime = "bull"
    elif bearish:
        market_regime = "bear"
    else:
        market_regime = "sideways"

    atr_pct = (atr / price) * 100 if price > 0 else 0
    volatility_context = "low" if atr_pct < 1 else "medium" if atr_pct < 2.5 else "high"

    recovery = price > ma50 and rsi > 40 and volume > avg_volume
    trend_change = ma50 > ma200 and df["ma50"].iloc[-2] < df["ma200"].iloc[-2]
    bearish_rebound = bearish and rsi < 45 and volume > avg_volume * 1.2

    # =========================
    # BUY
    # =========================
    if symbol not in symbols_open:
        if len(positions) >= MAX_POSITIONS:
            log(f"⚠ {symbol} máximo de posiciones alcanzado")
            add_last_decision(symbol, "SKIP", 0, "-", "max_positions")
            return

        if avg_dollar_volume < 50000:
            log(f"⚠ {symbol} bloqueado por volumen $ insuficiente | avg_$vol={avg_dollar_volume:.2f}")
            add_last_decision(symbol, "SKIP", 0, "low", "low_volume")
            return

        if not can_trade(symbol):
            log(f"⚠ {symbol} bloqueado por cooldown")
            add_last_decision(symbol, "SKIP", 0, "-", "cooldown")
            return

        if symbol_is_blocked(symbol):
            log(f"⚠ {symbol} bloqueado por symbol_filter")
            add_last_decision(symbol, "SKIP", 0, "-", "symbol_blocked")
            return

        now_dt = datetime.now(timezone.utc)
        vol_ratio = volume / avg_volume if avg_volume > 0 else 1

        today = now_dt.date()
        holiday_flags = get_holiday_flags(today)
        market_session = get_market_session(now_dt.hour)
        liquidity_mode = get_liquidity_mode(avg_dollar_volume, market_session, holiday_flags)

        log(
            f"INFO {symbol} | "
            f"liq={liquidity_mode} | "
            f"avg_vol={avg_volume:.2f} | "
            f"avg_$vol={avg_dollar_volume:.2f} | "
            f"regime={market_regime}"
        )

        if liquidity_mode == "low":
            log(f"⚠ {symbol} descartado por baja liquidez")
            add_last_decision(symbol, "SKIP", 0, liquidity_mode, "low_liquidity")
            return

        signals = evaluate_strategies({
            "price": price,
            "rsi": rsi,
            "ma50": ma50,
            "ma200": ma200,
            "volume": volume,
            "avg_volume": avg_volume,
            "momentum": price - ma50,
            "trend": price > ma50,
        })

        if not signals:
            log(f"⚠ {symbol} sin señales válidas")
            add_last_decision(symbol, "SKIP", 0, liquidity_mode, "no_signal")
            return

        pre_max_conf = max(float(s.get("confidence", 0)) for s in signals)

        ia_context = suggest_context_decision({
            "rsi": rsi,
            "volume": vol_ratio,
            "trend": int(price > ma50),
            "momentum": price - ma50,
            "hour": now_dt.hour,
            "day_of_week": now_dt.weekday(),
            "signal_confidence": pre_max_conf,
            "market_regime": market_regime,
            "atr": atr,
            "volatility_context": volatility_context,
        })

        ia_strategy = ia_context.get("strategy_suggestion")
        ia_risk = ia_context.get("risk_suggestion")

        best_signal = choose_signal_with_ai(signals, ia_strategy)

        if not best_signal:
            log(f"⚠ {symbol} IA no pudo elegir estrategia")
            add_last_decision(symbol, "SKIP", 0, liquidity_mode, "ai_strategy_none")
            return

        signal_confidence = float(best_signal.get("confidence", 0))
        strategy_name = str(best_signal.get("strategy", get_strategy_name()))
        signal_type = str(best_signal.get("type", "")).upper()

        log(
            f"🧠 IA estrategia | {symbol} | "
            f"sugerida={ia_strategy} | "
            f"elegida={strategy_name} | "
            f"type={signal_type} | "
            f"conf={signal_confidence:.2f}"
        )

        ai_decision = predict_trade({
            "rsi": rsi,
            "volume": vol_ratio,
            "trend": int(price > ma50),
            "momentum": price - ma50,
            "hour": now_dt.hour,
            "day_of_week": now_dt.weekday(),
            "signal_confidence": signal_confidence,
            "market_regime": market_regime,
            "atr": atr,
            "volatility_context": volatility_context,
            "liquidity_mode": liquidity_mode,
            "ai_context_risk": ia_risk,
        })

        system_winrate = get_winrate()
        total_closed_trades = get_total_closed_trades()

        log(f"DEBUG winrate={system_winrate} closed_trades={total_closed_trades}")

        trade_context = evaluate_trade_context(
            liquidity_mode=liquidity_mode,
            signal_confidence=signal_confidence,
            market_regime=market_regime,
            ai_decision=ai_decision,
            ia_risk=ia_risk,
            system_winrate=system_winrate,
            total_closed_trades=total_closed_trades,
            recovery=recovery,
            trend_change=trend_change,
            bearish_rebound=bearish_rebound,
        )

        log(
            f"INFO {symbol} | "
            f"liq={liquidity_mode} | "
            f"ai={ai_decision} | "
            f"conf={signal_confidence:.2f} | "
            f"regime={market_regime} | "
            f"strategy={strategy_name}"
        )

        if not trade_context["allow_trade"]:
            log(
                f"⛔ Trade bloqueado | "
                f"symbol={symbol} | "
                f"reason={trade_context['reason']} | "
                f"liquidity={liquidity_mode} | "
                f"ai_decision={ai_decision} | "
                f"ia_risk={ia_risk} | "
                f"confidence={signal_confidence:.2f} | "
                f"strategy={strategy_name}"
            )
            add_last_decision(
                symbol,
                "SKIP",
                signal_confidence,
                liquidity_mode,
                f"{trade_context['reason']}:{strategy_name}"
            )
            return

        risk_mode = trade_context["risk_mode_final"]
        required_conf = get_required_confidence(strategy_name)

        should_buy = (
            (signal_type == "BUY" and signal_confidence >= required_conf)
            or recovery
            or trend_change
            or bearish_rebound
        )

        if not should_buy:
            log(
                f"⚠ {symbol} no compra | "
                f"type={signal_type} | "
                f"conf={signal_confidence:.2f} | "
                f"required={required_conf:.2f} | "
                f"strategy={strategy_name} | "
                f"recovery={recovery} | "
                f"trend_change={trend_change} | "
                f"bearish_rebound={bearish_rebound}"
            )
            add_last_decision(
                symbol,
                "SKIP",
                signal_confidence,
                liquidity_mode,
                f"no_entry:{strategy_name}"
            )
            return

        try:
            balance_total = get_balance()
            balance_free = get_free_balance()

            if balance_free <= 0:
                log(f"⚠ {symbol} sin balance disponible")
                add_last_decision(symbol, "SKIP", signal_confidence, liquidity_mode, f"no_balance:{strategy_name}")
                return

            if not check_limits(balance_total):
                log(f"⚠ {symbol} bloqueado por límites de riesgo")
                add_last_decision(symbol, "SKIP", signal_confidence, liquidity_mode, f"risk_limits:{strategy_name}")
                return

            winrate = get_winrate()
            total_trades = get_total_closed_trades()

            if total_trades < 20:
                log(f"🔥 Warmup activo ({total_trades}/20 trades)")
            else:
                if winrate is not None and winrate < 0.40 and len(positions) > 2:
                    log(f"⛔ Trade bloqueado | low winrate {winrate:.2f}")
                    add_last_decision(symbol, "SKIP", signal_confidence, liquidity_mode, f"low_winrate:{strategy_name}")
                    return

            stop_loss_price = price * (1 + BEST_SL)

            risk_per_trade_used = RISK_PER_TRADE
            if risk_mode == "conservative":
                risk_per_trade_used *= 0.5
            elif risk_mode == "aggressive":
                risk_per_trade_used *= 1.25

            if total_trades < 20:
                risk_per_trade_used *= 0.5

            quantity = calculate_position_size(
                balance=balance_free,
                risk_per_trade=risk_per_trade_used,
                entry=price,
                stop=stop_loss_price,
            )

            if quantity <= 0:
                log(f"⚠ {symbol} quantity = 0")
                add_last_decision(symbol, "SKIP", signal_confidence, liquidity_mode, f"zero_quantity:{strategy_name}")
                return

            capital = min(quantity * price, balance_free * 0.2)
            quantity = round(capital / price, 6)

            tp_pct = get_dynamic_tp(strategy_name, volatility_context, BEST_TP, signal_confidence)
            take_profit_price = price * (1 + tp_pct)

            if quantity <= 0 or capital <= 0:
                log(f"⚠ {symbol} capital inválido | capital={capital} qty={quantity}")
                add_last_decision(symbol, "SKIP", signal_confidence, liquidity_mode, f"invalid_capital:{strategy_name}")
                return

            if not lock_balance(capital):
                log(f"⚠ {symbol} no pudo bloquear capital")
                add_last_decision(symbol, "SKIP", signal_confidence, liquidity_mode, f"lock_balance_failed:{strategy_name}")
                return

            add_position(
                symbol,
                price,
                quantity,
                capital,
                stop_loss_price,
                take_profit_price,
                extra={
                    "open_time": time.time(),
                    "partial_tp_done": False,
                    "strategy_name": strategy_name,
                    "tp_pct": tp_pct,
                }
            )

            open_time_data[symbol] = time.time()

            add_last_decision(
                symbol,
                "BUY",
                signal_confidence,
                liquidity_mode,
                f"ok:{strategy_name}"
            )

            log(
                f"✅ APERTURA | {symbol} | "
                f"entry={price:.6f} | "
                f"qty={quantity} | "
                f"capital={capital:.2f} | "
                f"risk_mode={risk_mode} | "
                f"conf={signal_confidence:.2f} | "
                f"strategy={strategy_name} | "
                f"tp_dynamic={tp_pct*100:.2f}%"
            )
            log_order(
                f"BUY | {symbol} | "
                f"entry={price:.6f} | "
                f"qty={quantity} | "
                f"capital={capital:.2f} | "
                f"strategy={strategy_name} | "
                f"risk_mode={risk_mode} | "
                f"tp={tp_pct*100:.2f}% | "
                f"sl={BEST_SL*100:.2f}%"
                
            )

            now_ts = int(now_dt.timestamp())

            register_trade({
                "symbol": symbol,
                "rsi": rsi,
                "volume": vol_ratio,
                "trend": int(price > ma50),
                "momentum": price - ma50,
                "result": "",
                "pnl": "",
                "timestamp": now_ts,
                "hour": now_dt.hour,
                "day_of_week": now_dt.weekday(),
                "signal_confidence": signal_confidence,
                "market_regime": market_regime,
                "strategy_name": strategy_name,
                "risk_mode": risk_mode,
                "atr": atr,
                "volatility_context": volatility_context,
                "market_session": market_session,

                "is_holiday_us": holiday_flags["is_holiday_us"],
                "holiday_name_us": us_holidays.get(today, ""),

                "is_holiday_ar": holiday_flags["is_holiday_ar"],
                "holiday_name_ar": ar_holidays.get(today, ""),

                "is_holiday_eu": holiday_flags["is_holiday_eu"],
                "holiday_name_eu": uk_holidays.get(today, "") or de_holidays.get(today, ""),

                "is_holiday_asia": holiday_flags["is_holiday_asia"],
                "holiday_name_asia": (
                    jp_holidays.get(today, "") or
                    cn_holidays.get(today, "") or
                    kr_holidays.get(today, "")
                ),

                "is_good_friday": holiday_flags["is_good_friday"],

                "liquidity_mode": liquidity_mode,
                "ai_trade_decision": ai_decision,
                "ai_context_risk": ia_risk or "",
                "trade_filter_reason": trade_context["reason"],

                "dataset_version": "live_ai_risk_v3",
                "risk_per_trade_used": risk_per_trade_used,
            })

            if mode == "real":
                log_order(f"REAL BUY | {symbol} | qty={quantity}")
                buy(symbol, quantity)

        except Exception as e:
            log(f"❌ Error al abrir posición: {e}")
            add_last_decision(
                symbol,
                "SKIP",
                signal_confidence if 'signal_confidence' in locals() else 0,
                liquidity_mode if 'liquidity_mode' in locals() else "-",
                f"open_error:{strategy_name if 'strategy_name' in locals() else 'unknown'}"
            )



 # =========================
        # SELL
 # =========================
    else:
        log(f"➡ SELL CHECK | {symbol}")
        try:
            update_position_extremes(symbol, price)

            pos = get_position(symbol)
            if not pos:
                log(f"⚠ {symbol} posición no encontrada")
                return

            entry = float(pos["entry_price"])
            quantity = float(pos["quantity"])
            capital = float(pos.get("capital", entry * quantity))
            current_max = float(pos.get("max_price", entry))
            current_min = float(pos.get("min_price", entry))
            partial_done = bool(pos.get("partial_tp_done", False))
            open_time = pos.get("open_time")

            profit_pct = (price - entry) / entry if entry > 0 else 0

            # =========================
            # ⏱ TIEMPO EN TRADE
            # =========================
            time_in_trade = 0
            if open_time:
                time_in_trade = time.time() - float(open_time)

            time_in_trade_min = time_in_trade / 60

            # =========================
            # 💰 PARTIAL TP
            # =========================
            if profit_pct >= 0.035 and not partial_done:
                partial_qty = quantity * 0.5
                partial_capital = capital * 0.5

                log_order(
                    f"PARTIAL SELL | {symbol} | "
                    f"price={price:.6f} | "
                    f"qty={partial_qty:.6f} | "
                    f"profit_pct={profit_pct*100:.2f}%"
                )

                pnl_partial = reduce_position(symbol, partial_qty, price)

                if mode == "real":
                    log_order(f"REAL PARTIAL SELL | {symbol} | qty={partial_qty:.6f}")
                    sell(symbol, partial_qty)

                unlock_balance(partial_capital, pnl_partial)

                # refrescar posición
                pos = get_position(symbol)
                if not pos:
                    return

                entry = float(pos["entry_price"])
                quantity = float(pos["quantity"])
                capital = float(pos.get("capital", entry * quantity))
                current_max = float(pos.get("max_price", entry))
                current_min = float(pos.get("min_price", entry))
                partial_done = bool(pos.get("partial_tp_done", False))
                open_time = pos.get("open_time")
                profit_pct = (price - entry) / entry if entry > 0 else 0

            # =========================
            # 🧠 TP dinámico REAL
            # =========================
            tp_pct = pos.get("tp_pct")
            if not tp_pct:
                tp_pct = BEST_TP

            # =========================
            # 🛡 BREAK EVEN SI YA HIZO PARCIAL
            # =========================
            effective_sl = BEST_SL
            if partial_done and profit_pct > 0:
                effective_sl = max(BEST_SL, -0.001)

            # =========================
            # ⏱ SALIDA POR TIEMPO
            # =========================
            time_exit = False
            # pérdida moderada temprana
            if time_in_trade_min > 30 and profit_pct < -0.01:
                time_exit = True
                log(f"⏱ EARLY LOSS CUT | {symbol}")

            # pérdida leve prolongada
            if time_in_trade_min > 90 and profit_pct < -0.005:
                time_exit = True
                log(f"⏱ TIME EXIT SMALL LOSS | {symbol}")

            # trade muerto total
            elif time_in_trade_min > 120:
                time_exit = True
                log(f"⏱ FORCE EXIT DEAD TRADE | {symbol}")

            # =========================
            # DEBUG
            # =========================
            log(
                f"DEBUG SELL | {symbol} | "
                f"entry={entry:.6f} | "
                f"price={price:.6f} | "
                f"profit_pct={profit_pct*100:.2f}% | "
                f"BEST_SL={BEST_SL*100:.2f}% | "
                f"tp_pct={tp_pct*100:.2f}% | "
                f"time_in_trade_min={time_in_trade_min:.1f} | "
                f"partial_done={partial_done}"
            )

            trailing_exit = update_trailing(symbol, price, atr, volatility_context, entry)
            tp_exit = profit_pct >= tp_pct
            sl_exit = profit_pct <= effective_sl

            log(
                f"DEBUG FLAGS | {symbol} | "
                f"trailing_exit={trailing_exit} | "
                f"tp_exit={tp_exit} | "
                f"sl_exit={sl_exit} | "
                f"time_exit={time_exit} | "
                f"effective_sl={effective_sl*100:.2f}%"
            )

            # =========================
            # 🎯 CONDICIÓN DE CIERRE
            # =========================
            should_close = (
                trailing_exit
                or tp_exit
                or sl_exit
                or time_exit
            )

            if should_close:
                close_reason = "unknown"
                if tp_exit:
                    close_reason = "take_profit"
                elif trailing_exit:
                    close_reason = "trailing"
                elif sl_exit:
                    close_reason = "stop_loss"
                elif time_exit:
                    close_reason = "time_exit"

                pnl_real = close_position(symbol, price)
                unlock_balance(capital, pnl_real)

                fee_entry = capital * 0.001
                fee_exit = max(capital + pnl_real, 0) * 0.001
                fee_total = fee_entry + fee_exit
                pnl_net = pnl_real - fee_total

                result = 1 if pnl_real > 0 else 0
                result_net = 1 if pnl_net > 0 else 0

                mfe_pct = ((current_max - entry) / entry) * 100 if entry > 0 else 0
                mae_pct = ((current_min - entry) / entry) * 100 if entry > 0 else 0

                log(
                    f"🔒 CIERRE | {symbol} | "
                    f"reason={close_reason} | "
                    f"pnl={pnl_real:.4f} | "
                    f"pnl_net={pnl_net:.4f} | "
                    f"profit_pct={profit_pct*100:.2f}% | "
                    f"time={time_in_trade_min:.1f}min"
                )

                log_order(
                    f"SELL | {symbol} | "
                    f"reason={close_reason} | "
                    f"price={price:.6f} | "
                    f"qty={quantity:.6f} | "
                    f"pnl={pnl_real:.4f} | "
                    f"pnl_net={pnl_net:.4f} | "
                    f"profit_pct={profit_pct*100:.2f}% | "
                    f"time={time_in_trade_min:.1f}m"
                )

                update_trade_result(
                    symbol,
                    result,
                    pnl_real,
                    mfe_pct,
                    mae_pct,
                    fee_entry,
                    fee_exit,
                    fee_total,
                    pnl_net,
                    result_net
                )

                if mode == "real":
                    log_order(f"REAL SELL | {symbol} | qty={quantity:.6f}")
                    sell(symbol, quantity)

                trailing_data.pop(symbol, None)

        except Exception as e:
            log(f"❌ Error cerrando {symbol}: {e}")
# =========================
# LOOP
# =========================
def run_cycle():
    maybe_retrain()

    for pos in get_open_positions():
        process_symbol(pos["symbol"])

    raw_ops = rank_symbols(scan_market())
    ops = []

    for op in raw_ops:
        symbol = op.get("symbol") or op.get("pair")
        if symbol and is_valid_trade_symbol(symbol):
            ops.append(op)

    log(f"📊 Total oportunidades detectadas: {len(raw_ops)}")
    log(f"✅ Oportunidades válidas: {len(ops)}")

    valid_symbols = []

    for op in ops[:15]:
        symbol = op.get("symbol") or op.get("pair")
        if symbol:
            valid_symbols.append(symbol)
            log(f"🔎 Analizando: {symbol}")
            process_symbol(symbol)

    log(f"✅ Símbolos enviados a análisis: {len(valid_symbols)} | {valid_symbols}")


def start_bot():
    while True:
        if not is_running():
            time.sleep(5)
            continue

        try:
            run_cycle()
        except Exception as e:
            log(f"🔥 Error: {e}")

        time.sleep(30)


if __name__ == "__main__":
    ensure_trades_file()
    start_bot()