import time
import holidays
import re
import pandas as pd
from datetime import datetime, timezone, timedelta, date
from services.daily_snapshot_service import upsert_today_snapshot
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
    stop_bot_state,
    should_stop_after_close,
)

from portfolio import get_balance, get_free_balance, lock_balance, unlock_balance
from executor import buy, sell
from ai_auto_trainer import maybe_retrain
from ai_strategy_learner import suggest_context_decision
from services.dashboard_service import add_last_decision
from logger import log, log_order
from services.daily_stats_service import save_daily_stats_json
from AI import TradePredictionManager

prediction_manager = TradePredictionManager()

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
post_loss_cooldown = {}


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
# MÉTRICAS DIARIAS POR SÍMBOLO
# =========================
from datetime import datetime, timezone

def get_daily_pnl(symbol):
    try:
        df = pd.read_csv("trades_dataset.csv")

        today = datetime.now(timezone.utc).date()

        df["date"] = pd.to_datetime(df["timestamp"], unit="s").dt.date

        df_today = df[
            (df["symbol"] == symbol) &
            (df["date"] == today)
        ]

        pnl = df_today["pnl_net"].dropna()

        return pnl.sum() if len(pnl) > 0 else 0

    except Exception as e:
        log(f"⚠ error get_daily_pnl {symbol}: {e}")
        return 0


def count_daily_losses(symbol):
    try:
        df = pd.read_csv("trades_dataset.csv")

        today = datetime.now(timezone.utc).date()

        df["date"] = pd.to_datetime(df["timestamp"], unit="s").dt.date

        df_today = df[
            (df["symbol"] == symbol) &
            (df["date"] == today)
        ]

        losses = df_today[df_today["pnl_net"] < 0]

        return len(losses)

    except Exception as e:
        log(f"⚠ error count_daily_losses {symbol}: {e}")
        return 0

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

        # =========================
        # COOLDOWN POST-PÉRDIDA
        # =========================
        cooldown_until = post_loss_cooldown.get(symbol, 0)
        if time.time() < cooldown_until:
            mins_left = int((cooldown_until - time.time()) / 60) + 1
            log(f"⛔ {symbol} cooldown post-pérdida activo | faltan {mins_left}m")
            add_last_decision(symbol, "SKIP", 0, "-", "post_loss_cooldown")
            return

        # =========================
        # LÍMITE DE PÉRDIDAS DIARIAS
        # =========================
        daily_losses = count_daily_losses(symbol)
        daily_pnl = get_daily_pnl(symbol)

        risk_per_trade_typical = 0.02
        balance = get_balance()
        max_daily_loss_per_symbol = balance * risk_per_trade_typical * 2

        if daily_losses >= 3:
            log(f"⛔ {symbol} bloqueado | {daily_losses} pérdidas hoy")
            add_last_decision(symbol, "SKIP", 0, "-", "daily_loss_limit")
            return

        if daily_pnl < -max_daily_loss_per_symbol:
            log(
                f"⛔ {symbol} bloqueado | "
                f"pnl diario {daily_pnl:.2f} < {-max_daily_loss_per_symbol:.2f}"
            )
            add_last_decision(symbol, "SKIP", 0, "-", "daily_pnl_limit")
            return

        if daily_losses >= 2 and daily_pnl < -(max_daily_loss_per_symbol * 0.5):
            log(f"⚠️ {symbol} en alerta | {daily_losses} pérdidas, pnl {daily_pnl:.2f}")

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

        # =========================
        # ANTI FAST SL FILTER
        # =========================
        momentum_pct = (price - ma50) / ma50 if ma50 > 0 else 0
        distance_from_ma50 = abs(price - ma50) / ma50 if ma50 > 0 else 0

        if strategy_name.lower() == "mean_reversion":

            # 1. CAÍDA FUERTE ACTIVA
            if momentum_pct < -0.02:
                log(f"⛔ {symbol} skip | caída fuerte activa {momentum_pct:.2%}")
                add_last_decision(symbol, "SKIP", signal_confidence, liquidity_mode, "fastsl_strong_drop")
                return

            # 2. SIN DESVIACIÓN SUFICIENTE
            if distance_from_ma50 < 0.012:
                log(f"⚠ {symbol} skip | sin desviación suficiente {distance_from_ma50:.2%}")
                add_last_decision(symbol, "SKIP", signal_confidence, liquidity_mode, "fastsl_no_deviation")
                return

            # 3. REBOTE CONFIRMADO
            if df is not None and len(df) >= 3:
                c1 = df["close"].iloc[-1]
                c2 = df["close"].iloc[-2]

                rebound_thresholds = {
                    "low": 1.003,     # +0.3%
                    "medium": 1.005,  # +0.5%
                    "high": 1.008,    # +0.8%
                }
                rebound_factor = rebound_thresholds.get(volatility_context, 1.005)

                if not (c1 > c2 * rebound_factor):
                    log(
                        f"⛔ {symbol} skip | sin rebote suficiente | "
                        f"need=+{(rebound_factor - 1) * 100:.2f}% | "
                        f"c1={c1:.6f} c2={c2:.6f}"
                    )
                    add_last_decision(symbol, "SKIP", signal_confidence, liquidity_mode, "fastsl_no_rebound")
                    return

            # 4. VOLUMEN DÉBIL
            if volume < avg_volume * 0.7:
                log(f"⚠ {symbol} skip | volumen débil {volume/avg_volume:.1%}")
                add_last_decision(symbol, "SKIP", signal_confidence, liquidity_mode, "fastsl_low_volume")
                return

            # 5. ALTA VOLATILIDAD SIN CONFIANZA
            if volatility_context == "high" and signal_confidence < 0.75:
                log(f"⚠ {symbol} skip | alta vol sin confianza {signal_confidence:.2f}")
                add_last_decision(symbol, "SKIP", signal_confidence, liquidity_mode, "fastsl_high_volatility")
                return

            log(
                f"✅ {symbol} anti-FAST_SL OK | "
                f"momentum={momentum_pct:.2%} | "
                f"dist={distance_from_ma50:.2%}"
            )

        # =========================
        # IA VIEJA -> DECISIÓN REAL
        # =========================
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

        # =========================
        # IA NUEVA -> MODO SOMBRA
        # =========================
        shadow_prediction = ""
        prob_live = ""
        prob_historical = ""
        prob_final = ""
        decision_source = ""
        models_agree = ""

        try:
            shadow_result = prediction_manager.predict({
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

            shadow_prediction = int(shadow_result.get("prediction", 0))
            prob_live = float(shadow_result.get("live_result", {}).get("probability_win", 0.0))
            prob_historical = float(shadow_result.get("historical_result", {}).get("probability_win", 0.0))
            prob_final = float(shadow_result.get("probability_win", 0.0))
            decision_source = str(shadow_result.get("manager_mode", "unknown"))

            live_pred = shadow_result.get("live_result", {}).get("prediction")
            hist_pred = shadow_result.get("historical_result", {}).get("prediction")
            models_agree = int(
                live_pred is not None and hist_pred is not None and live_pred == hist_pred
            )

            log(
                f"👁 IA SOMBRA | {symbol} | "
                f"shadow_pred={shadow_prediction} | "
                f"prob_live={prob_live:.4f} | "
                f"prob_hist={prob_historical:.4f} | "
                f"prob_final={prob_final:.4f} | "
                f"source={decision_source} | "
                f"agree={models_agree}"
            )

        except Exception as e:
            log(f"⚠ IA sombra error {symbol}: {e}")

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

        # =========================
        # FILTROS DE CALIDAD DE ENTRADA
        # =========================
        risk_mode = trade_context["risk_mode_final"]
        required_conf = get_required_confidence(strategy_name)

        if market_regime == "sideways":
            required_conf = max(required_conf, 0.80)

        if market_regime == "sideways" and atr_pct < 1.2:
            log(f"⚠ {symbol} skip sideways sin rango | atr_pct={atr_pct:.2f}%")
            add_last_decision(
                symbol,
                "SKIP",
                signal_confidence,
                liquidity_mode,
                f"sideways_low_range:{strategy_name}"
            )
            return

        if strategy_name.lower() == "mean_reversion":
            if rsi > 60:
                log(f"⚠ {symbol} skip MR RSI alto | rsi={rsi:.2f}")
                add_last_decision(
                    symbol,
                    "SKIP",
                    signal_confidence,
                    liquidity_mode,
                    f"mr_rsi_high:{strategy_name}"
                )
                return

            if momentum_pct > 0.02:
                log(f"⚠ {symbol} skip MR sobreextendido | momentum={momentum_pct:.2%}")
                add_last_decision(
                    symbol,
                    "SKIP",
                    signal_confidence,
                    liquidity_mode,
                    f"mr_overextended:{strategy_name}"
                )
                return

            if distance_from_ma50 < 0.01:
                log(f"⚠ {symbol} skip MR sin desviación | dist={distance_from_ma50:.2%}")
                add_last_decision(
                    symbol,
                    "SKIP",
                    signal_confidence,
                    liquidity_mode,
                    f"mr_no_deviation:{strategy_name}"
                )
                return

        exceptional_setup = recovery or trend_change or bearish_rebound
        min_exception_confidence = 0.75

        should_buy = (
            (signal_type == "BUY" and signal_confidence >= required_conf)
            or (exceptional_setup and signal_confidence >= min_exception_confidence)
        )

        if not should_buy:
            log(
                f"⚠ {symbol} no compra | "
                f"type={signal_type} | "
                f"conf={signal_confidence:.2f} | "
                f"required={required_conf:.2f} | "
                f"strategy={strategy_name} | "
                f"exceptional={exceptional_setup} | "
                f"min_exc_conf={min_exception_confidence:.2f}"
            )
            add_last_decision(
                symbol,
                "SKIP",
                signal_confidence,
                liquidity_mode,
                f"no_entry:{strategy_name}"
            )
            return

        # =========================
        # CÁLCULO DE POSICIÓN
        # =========================
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

            sl_pct = abs(BEST_SL)
            stop_loss_price = price * (1 - sl_pct)

            risk_per_trade_used = RISK_PER_TRADE
            if risk_mode == "conservative":
                risk_per_trade_used *= 0.5
            elif risk_mode == "aggressive":
                risk_per_trade_used *= 1.25

            if total_trades < 20:
                risk_per_trade_used *= 0.5

            risk_amount = balance_free * risk_per_trade_used

            if sl_pct > 0:
                position_value = risk_amount / sl_pct
                max_exposure = balance_free * 0.25
                capital = min(position_value, max_exposure)
            else:
                capital = 0

            quantity = round(capital / price, 6)

            min_order_value = 10
            if capital < min_order_value:
                log(f"⚠ {symbol} capital insuficiente | ${capital:.2f} < ${min_order_value}")
                add_last_decision(symbol, "SKIP", signal_confidence, liquidity_mode, f"min_order:{strategy_name}")
                return

            if quantity <= 0:
                log(f"⚠ {symbol} quantity = 0")
                add_last_decision(symbol, "SKIP", signal_confidence, liquidity_mode, f"zero_quantity:{strategy_name}")
                return

            exposure_pct = (capital / balance_free) * 100 if balance_free > 0 else 0
            if exposure_pct > 20:
                log(f"⚠️ ALTA EXPOSICIÓN | {symbol} | {exposure_pct:.1f}% del balance")

            tp_pct = get_dynamic_tp(strategy_name, volatility_context, BEST_TP, signal_confidence)
            take_profit_price = price * (1 + tp_pct)

            log(
                f"📊 POSITION CALC | {symbol} | "
                f"risk=${risk_amount:.2f} | "
                f"capital=${capital:.2f} | "
                f"qty={quantity} | "
                f"entry={price:.6f} | "
                f"sl={stop_loss_price:.6f} ({-sl_pct*100:.2f}%) | "
                f"tp={take_profit_price:.6f} ({tp_pct*100:.2f}%)"
            )

            # =========================
            # EJECUCIÓN CON ROLLBACK
            # =========================
            capital_locked = False
            position_added = False

            try:
                if not lock_balance(capital):
                    raise Exception("No se pudo bloquear capital")
                capital_locked = True

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
                        "original_sl": -sl_pct,
                        "risk_mode": risk_mode,
                    }
                )
                position_added = True

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
                    f"sl={-sl_pct*100:.2f}%"
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
                    "shadow_prediction": shadow_prediction,
                    "prob_live": prob_live,
                    "prob_historical": prob_historical,
                    "prob_final": prob_final,
                    "decision_source": decision_source,
                    "models_agree": models_agree,
                    "ai_context_risk": ia_risk or "",
                    "trade_filter_reason": trade_context["reason"],
                    "dataset_version": "live_ai_risk_v3",
                    "risk_per_trade_used": risk_per_trade_used,
                })

                try:
                    save_daily_stats_json()
                    log(f"📊 daily_stats.json actualizado | {symbol}")
                except Exception as e:
                    log(f"⚠ Error actualizando daily stats: {e}")

                if mode == "real":
                    log_order(f"REAL BUY | {symbol} | qty={quantity}")
                    buy(symbol, quantity)

            except Exception as exec_error:
                if capital_locked and not position_added:
                    log("🔄 Rollback: Liberando capital bloqueado por error")
                    unlock_balance(capital, 0)
                raise exec_error

        except Exception as e:
            log(f"❌ Error al abrir posición {symbol}: {e}")
            add_last_decision(
                symbol,
                "ERROR",
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

            # =========================
            # 📊 DATOS BASE
            # =========================
            entry = float(pos["entry_price"])
            quantity = float(pos["quantity"])
            capital = float(pos.get("capital", entry * quantity))
            current_max = float(pos.get("max_price", entry))
            current_min = float(pos.get("min_price", entry))
            partial_done = bool(pos.get("partial_tp_done", False))
            open_time = pos.get("open_time")

            profit_pct = (price - entry) / entry if entry > 0 else 0

            time_in_trade_min = 0
            if open_time:
                time_in_trade_min = (time.time() - float(open_time)) / 60.0

            tp_pct = pos.get("tp_pct") or BEST_TP

            # =========================
            # 💰 PARTIAL TP
            # =========================
            if profit_pct >= 0.035 and not partial_done:
                partial_pct = 0.50
                partial_qty = quantity * partial_pct
                partial_capital = capital * partial_pct

                log_order(
                    f"PARTIAL SELL | {symbol} | "
                    f"price={price:.6f} | qty={partial_qty:.6f} | "
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
                time_in_trade_min = 0
                if open_time:
                    time_in_trade_min = (time.time() - float(open_time)) / 60.0

            # =========================
            # 📈 VARIABLES DE CONTROL
            # =========================
            progress = profit_pct / tp_pct if tp_pct > 0 else 0
            range_pct = (current_max - entry) / entry if entry > 0 else 0

            log(
                f"DEBUG VARS | {symbol} | "
                f"profit_pct={profit_pct*100:.2f}% | "
                f"tp_pct={tp_pct*100:.2f}% | "
                f"progress={progress:.2f} | "
                f"time_in_trade={time_in_trade_min:.1f}min | "
                f"range_pct={range_pct*100:.2f}% | "
                f"partial_done={partial_done}"
            )

            # =========================
            # 🎯 EVALUACIÓN DE SALIDAS
            # =========================
            should_close = False
            close_reason = ""
            exit_type = ""

            # -------------------------------------------------
            # 0. FAST LOSS PROTECTION
            # -------------------------------------------------
            if not should_close and not partial_done and time_in_trade_min <= 15:
                fast_loss_thresholds = {
                    "low": -0.008,
                    "medium": -0.010,
                    "high": -0.015,
                }
                fast_loss_limit = fast_loss_thresholds.get(volatility_context, -0.005)

                if profit_pct < fast_loss_limit:
                    should_close = True
                    close_reason = f"fast_loss_{volatility_context}_{fast_loss_limit*100:.1f}%"
                    exit_type = "FAST_SL"
                    log(
                        f"🚨 EXIT TRIGGER: FAST LOSS | {symbol} | "
                        f"profit={profit_pct*100:.2f}% | "
                        f"time={time_in_trade_min:.1f}min | "
                        f"vol={volatility_context} | "
                        f"limit={fast_loss_limit*100:.1f}%"
                    )

            # -------------------------------------------------
            # 1. STOP LOSS
            # -------------------------------------------------
            effective_sl = float(BEST_SL)

            if partial_done:
                if profit_pct > 0.03:
                    effective_sl = 0.005      # +0.5%
                elif profit_pct > 0:
                    effective_sl = -0.005     # -0.5%
                else:
                    effective_sl = BEST_SL * 0.5

            if not should_close and profit_pct <= effective_sl:
                should_close = True
                close_reason = f"stop_loss_{effective_sl*100:.2f}%"
                exit_type = "SL"
                log(
                    f"🛑 EXIT TRIGGER: SL | {symbol} | "
                    f"profit={profit_pct*100:.2f}% | "
                    f"sl_level={effective_sl*100:.2f}%"
                )

            # -------------------------------------------------
            # 2. TRAILING STOP
            # -------------------------------------------------
            if not should_close:
                if symbol not in trailing_data:
                    trailing_data[symbol] = {"max_price": price, "current_stop": None}

                if price > trailing_data[symbol]["max_price"]:
                    trailing_data[symbol]["max_price"] = price

                max_price = trailing_data[symbol]["max_price"]

                if profit_pct >= 0.015:
                    multipliers = {
                        "low": 1.5,
                        "medium": 2.0,
                        "high": 3.0,
                    }
                    multiplier = multipliers.get(volatility_context, 2.0)

                    if partial_done:
                        multiplier *= 1.3

                    trailing_stop = max_price - (atr * multiplier)

                    log(
                        f"DEBUG TRAILING | {symbol} | "
                        f"max_price={max_price:.6f} | "
                        f"trailing_stop={trailing_stop:.6f} | "
                        f"current={price:.6f} | "
                        f"multiplier={multiplier:.1f}"
                    )

                    if price <= trailing_stop:
                        should_close = True
                        close_reason = "trailing_stop"
                        exit_type = "TRAILING"
                        log(
                            f"🛑 EXIT TRIGGER: TRAILING | {symbol} | "
                            f"max_profit={(max_price-entry)/entry*100:.2f}% | "
                            f"giveback={(max_price-price)/entry*100:.2f}%"
                        )

            # -------------------------------------------------
            # 3. TAKE PROFIT
            # -------------------------------------------------
            if not should_close:
                tp_hit = False
                tp_reason = ""

                if profit_pct >= tp_pct:
                    if partial_done:
                        if market_regime == "bull" and volatility_context != "high":
                            extended_tp = tp_pct * 1.5
                            if profit_pct >= extended_tp:
                                tp_hit = True
                                tp_reason = f"extended_tp_{extended_tp*100:.1f}%"
                            else:
                                log(
                                    f"DEBUG TP | {symbol} | "
                                    f"holding_for_extended={extended_tp*100:.1f}% | "
                                    f"current={profit_pct*100:.2f}%"
                                )
                        else:
                            tp_hit = True
                            tp_reason = "tp_after_partial"
                    else:
                        tp_hit = True
                        tp_reason = "standard_tp"

                if tp_hit:
                    should_close = True
                    close_reason = tp_reason
                    exit_type = "TP"
                    log(
                        f"🎯 EXIT TRIGGER: TP | {symbol} | "
                        f"tp_pct={tp_pct*100:.2f}% | "
                        f"achieved={profit_pct*100:.2f}% | "
                        f"progress={progress:.2f}"
                    )

            # -------------------------------------------------
            # 4. DEAD TRADE (más permisivo)
            # -------------------------------------------------
            if not should_close:
                dead_conditions = 0
                dead_reasons = []
                dead_trade_exit = False

                min_grace_period = 35

                if time_in_trade_min < min_grace_period:
                    log(
                        f"DEBUG DEAD | {symbol} | "
                        f"grace_period_active | time={time_in_trade_min:.1f}m"
                    )
                else:
                    if profit_pct > 0.003:
                        log(
                            f"DEBUG DEAD | {symbol} | "
                            f"profit_protect | profit={profit_pct:.3%} | NO EVALUAR"
                        )
                        dead_trade_exit = False

                    elif profit_pct > 0:
                        time_limits = {"bull": 120, "sideways": 90, "bear": 60}
                        time_limit = time_limits.get(market_regime, 90)

                        if time_in_trade_min > time_limit:
                            dead_conditions += 1
                            dead_reasons.append(f"flat_time>{time_limit}m")

                        if progress < 0.02:
                            dead_conditions += 1
                            dead_reasons.append(f"extremely_slow<{progress:.2f}")

                        min_expected_range = min(0.015, 0.005 * (time_in_trade_min / 30))
                        if range_pct < min_expected_range:
                            dead_conditions += 1
                            dead_reasons.append(f"flat_range<{min_expected_range:.2%}")

                        dead_trade_exit = dead_conditions >= 4

                    else:
                        time_limits = {"bull": 90, "sideways": 60, "bear": 45}
                        time_limit = time_limits.get(market_regime, 60)

                        if time_in_trade_min > time_limit:
                            dead_conditions += 1
                            dead_reasons.append(f"time>{time_limit}m")

                        if profit_pct < -0.007:
                            dead_conditions += 1
                            dead_reasons.append("negative_progress")

                        if profit_pct < -0.01:
                            dead_conditions += 2
                            dead_reasons.append(f"significant_loss>{profit_pct:.2%}")

                        base_range = 0.01
                        if volatility_context == "low":
                            range_threshold = base_range * 0.5   # 0.5%
                        elif volatility_context == "medium":
                            range_threshold = base_range * 0.8   # 0.8%
                        else:
                            range_threshold = base_range * 1.2   # 1.2%

                        if range_pct < range_threshold:
                            dead_conditions += 1
                            dead_reasons.append(f"range<{range_threshold:.2%}")

                        if 'df' in locals() and df is not None and len(df) >= 10:
                            recent_velocity = df['close'].pct_change().abs().iloc[-10:].mean()
                            if recent_velocity < 0.0002:
                                dead_conditions += 1
                                dead_reasons.append(f"velocity<{recent_velocity:.4f}")

                        dead_trade_exit = dead_conditions >= 4

                log(
                    f"DEBUG DEAD | {symbol} | "
                    f"conditions={dead_conditions} | "
                    f"details={dead_reasons if dead_reasons else 'none'} | "
                    f"time={time_in_trade_min:.1f}m | "
                    f"profit={profit_pct*100:.2f}% | "
                    f"range={range_pct*100:.2f}% | "
                    f"dead={dead_trade_exit}"
                )

                if dead_trade_exit:
                    should_close = True
                    close_reason = f"dead_trade:{','.join(dead_reasons)}"
                    exit_type = "DEAD"
                    log(
                        f"☠ EXIT TRIGGER: DEAD TRADE | {symbol} | "
                        f"time={time_in_trade_min:.1f}m | "
                        f"profit={profit_pct*100:.2f}% | "
                        f"progress={progress:.2f} | "
                        f"range={range_pct*100:.2f}%"
                    )

            # -------------------------------------------------
            # 5. TIME EXIT
            # -------------------------------------------------
            if not should_close:
                time_hit = False
                time_reason = ""

                if profit_pct < 0.02:
                    early_cut = {"bull": 45, "sideways": 30, "bear": 20}
                    small_loss = {"bull": 120, "sideways": 90, "bear": 60}
                    max_time = {"bull": 240, "sideways": 180, "bear": 120}

                    if time_in_trade_min > early_cut.get(market_regime, 30) and profit_pct < -0.015:
                        time_hit = True
                        time_reason = f"early_cut_{market_regime}"
                    elif time_in_trade_min > small_loss.get(market_regime, 90) and profit_pct < -0.008:
                        time_hit = True
                        time_reason = f"small_loss_{market_regime}"
                    elif time_in_trade_min > max_time.get(market_regime, 180):
                        time_hit = True
                        time_reason = f"max_time_{market_regime}"

                log(
                    f"DEBUG TIME | {symbol} | "
                    f"time={time_in_trade_min:.1f}min | "
                    f"triggered={time_hit}"
                )

                # No cerrar por tiempo si ya tiene ganancia decente
                if time_hit and profit_pct > 0.015:
                    log(
                        f"⏱ TIME EXIT CANCELADO | {symbol} | "
                        f"profit={profit_pct*100:.2f}%"
                    )
                    time_hit = False
                    time_reason = ""

                if time_hit:
                    should_close = True
                    close_reason = time_reason
                    exit_type = "TIME"
                    log(
                        f"⏱ EXIT TRIGGER: TIME | {symbol} | "
                        f"reason={time_reason} | "
                        f"final_profit={profit_pct*100:.2f}%"
                    )

            # =========================
            # 💰 FILTRO RENTABLE (MODO PRO)
            # =========================
            fee_buffer = 0.004  # 0.4%
            min_real_profit = fee_buffer

            force_close = (
                exit_type in ["SL", "FAST_SL"]
                or profit_pct < -0.01
            )

            if should_close and not force_close:
                if profit_pct < min_real_profit:
                    log(
                        f"⛔ BLOQUEO CIERRE | {symbol} | "
                        f"profit={profit_pct*100:.2f}% < min_real={min_real_profit*100:.2f}% | "
                        f"type={exit_type}"
                    )
                    should_close = False
                    close_reason = ""
                    exit_type = ""

            # =========================
            # 🔒 EJECUCIÓN DEL CIERRE
            # =========================
            if should_close:
                log(
                    f"✅ EXECUTING CLOSE | {symbol} | "
                    f"type={exit_type} | "
                    f"reason={close_reason} | "
                    f"profit={profit_pct*100:.2f}% | "
                    f"time={time_in_trade_min:.1f}min"
                )

                pnl_real = close_position(symbol, price)
                unlock_balance(capital, pnl_real)

                fee_entry = capital * 0.001
                fee_exit = max(capital + pnl_real, 0) * 0.001
                fee_total = fee_entry + fee_exit
                pnl_net = pnl_real - fee_total

                # =========================
                # COOLDOWN POST-PÉRDIDA POR SÍMBOLO
                # =========================
                if pnl_net < 0:
                    cooldown_seconds = 1800  # 30 min base

                    if exit_type in ["FAST_SL", "SL"]:
                        cooldown_seconds = 3600  # 60 min si fue salida dura

                    post_loss_cooldown[symbol] = time.time() + cooldown_seconds

                    log(
                        f"⛔ POST-LOSS COOLDOWN | {symbol} | "
                        f"type={exit_type} | "
                        f"pnl_net={pnl_net:.4f} | "
                        f"cooldown={cooldown_seconds // 60}m"
                    )
                else:
                    post_loss_cooldown.pop(symbol, None)

                result = 1 if pnl_real > 0 else 0
                result_net = 1 if pnl_net > 0 else 0

                mfe_pct = ((current_max - entry) / entry) * 100 if entry > 0 else 0
                mae_pct = ((current_min - entry) / entry) * 100 if entry > 0 else 0

                log(
                    f"🔒 CIERRE | {symbol} | "
                    f"type={exit_type} | "
                    f"reason={close_reason} | "
                    f"pnl={pnl_real:.4f} | "
                    f"pnl_net={pnl_net:.4f} | "
                    f"profit_pct={profit_pct*100:.2f}% | "
                    f"time={time_in_trade_min:.1f}min | "
                    f"MFE={mfe_pct:.2f}% | "
                    f"MAE={mae_pct:.2f}%"
                )

                log_order(
                    f"SELL | {symbol} | "
                    f"type={exit_type} | "
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
                open_time_data.pop(symbol, None)

            else:
                log(
                    f"⏸ HOLD | {symbol} | "
                    f"profit={profit_pct*100:.2f}% | "
                    f"progress={progress:.2f} | "
                    f"time={time_in_trade_min:.1f}min"
                )

        except Exception as e:
            log(f"❌ Error cerrando {symbol}: {e}")
            import traceback
            log(traceback.format_exc())
# =========================
# LOOP OPTIMIZADO
# =========================
last_entry_check = 0


def run_cycle():
    global last_entry_check

    log("🔄 run_cycle iniciado")
    maybe_retrain()

    # =========================
    # 1) SIEMPRE gestionar posiciones abiertas
    # =========================
    open_positions = get_open_positions()

    if open_positions:
        log(f"📂 Posiciones abiertas: {len(open_positions)}")

    for pos in open_positions:
        try:
            process_symbol(pos["symbol"])
        except Exception as e:
            log(f"❌ Error procesando SELL {pos.get('symbol')}: {e}")

    # refrescar por si alguna cerró en este mismo ciclo
    open_positions = get_open_positions()

    # =========================
    # 2) MODO APAGADO SUAVE
    # =========================
    if should_stop_after_close():
        if len(open_positions) == 0:
            log("🛑 Soft stop completado | no quedan posiciones abiertas")
            stop_bot_state()
        else:
            log(f"⏳ Soft stop activo | esperando cerrar {len(open_positions)} posiciones")
        return

    # =========================
    # 3) NUEVAS ENTRADAS SOLO SI NO HAY SOFT STOP
    # =========================
    now = time.time()

    if now - last_entry_check < 60:
        remaining = int(60 - (now - last_entry_check))
        log(f"⏳ Saltando búsqueda de entradas | próximo scan en {remaining}s")
        return

    last_entry_check = now
    log("🔎 Iniciando scan de nuevas entradas")

    try:
        raw_ops = rank_symbols(scan_market())
    except Exception as e:
        log(f"❌ Error en scan_market/rank_symbols: {e}")
        return

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
            log(f"🔎 Analizando BUY: {symbol}")

            try:
                process_symbol(symbol)
            except Exception as e:
                log(f"❌ Error procesando BUY {symbol}: {e}")

    log(f"✅ Símbolos enviados a análisis BUY: {len(valid_symbols)} | {valid_symbols}")


def start_bot():
    log("🤖 BOT STARTED")

    while True:
        try:
            if not is_running():
                log("⏸ Bot pausado")
                time.sleep(5)
                continue

            log("🚀 Ejecutando run_cycle()")
            run_cycle()
            log("✅ run_cycle finalizado")

        except Exception as e:
            log(f"🔥 ERROR LOOP: {e}")

        time.sleep(20)


if __name__ == "__main__":
    ensure_trades_file()
    log("🚀 Iniciando bot...")
    start_bot()