from pprint import pprint

from AI import (
    HistoricalTradePredictor,
    TradePredictor,
    TradePredictionManager,
    suggest_context_decision,
)
from AI.logger import log_ai_decision


def print_header(title: str):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def print_result_block(name: str, result: dict):
    print(f"\n[{name}]")
    pprint(result)


def main():
    historical = HistoricalTradePredictor()
    live = TradePredictor()
    manager = TradePredictionManager()

    scenarios = {
        "bull_fuerte_reversion": {
            "rsi": 24,
            "volume": 2.4,
            "trend": 1,
            "momentum": 0.9,
            "hour": 14,
            "day_of_week": 2,
            "signal_confidence": 0.88,
            "atr": 0.018,
            "market_regime": "bull",
            "volatility_context": "medium",
            "liquidity_mode": "normal",
            "ai_context_risk": "normal",
        },
        "bear_debil": {
            "rsi": 41,
            "volume": 0.8,
            "trend": 0,
            "momentum": -0.7,
            "hour": 16,
            "day_of_week": 3,
            "signal_confidence": 0.52,
            "atr": 0.021,
            "market_regime": "bear",
            "volatility_context": "medium",
            "liquidity_mode": "normal",
            "ai_context_risk": "conservative",
        },
        "sideways_dudoso": {
            "rsi": 49,
            "volume": 0.95,
            "trend": 0,
            "momentum": 0.03,
            "hour": 11,
            "day_of_week": 1,
            "signal_confidence": 0.51,
            "atr": 0.012,
            "market_regime": "sideways",
            "volatility_context": "low",
            "liquidity_mode": "normal",
            "ai_context_risk": "normal",
        },
        "alta_volatilidad": {
            "rsi": 29,
            "volume": 3.1,
            "trend": 1,
            "momentum": 1.4,
            "hour": 10,
            "day_of_week": 4,
            "signal_confidence": 0.73,
            "atr": 0.065,
            "market_regime": "bull",
            "volatility_context": "high",
            "liquidity_mode": "normal",
            "ai_context_risk": "conservative",
        },
        "baja_liquidez": {
            "rsi": 27,
            "volume": 0.35,
            "trend": 1,
            "momentum": 0.4,
            "hour": 2,
            "day_of_week": 5,
            "signal_confidence": 0.79,
            "atr": 0.02,
            "market_regime": "bull",
            "volatility_context": "medium",
            "liquidity_mode": "low",
            "ai_context_risk": "normal",
        },
        "setup_muy_fuerte": {
            "rsi": 18,
            "volume": 4.2,
            "trend": 1,
            "momentum": 1.8,
            "hour": 13,
            "day_of_week": 2,
            "signal_confidence": 0.93,
            "atr": 0.022,
            "market_regime": "bull",
            "volatility_context": "medium",
            "liquidity_mode": "normal",
            "ai_context_risk": "aggressive",
        },
        "setup_malo_claro": {
            "rsi": 67,
            "volume": 0.55,
            "trend": 0,
            "momentum": -1.2,
            "hour": 20,
            "day_of_week": 0,
            "signal_confidence": 0.34,
            "atr": 0.03,
            "market_regime": "bear",
            "volatility_context": "high",
            "liquidity_mode": "low",
            "ai_context_risk": "conservative",
        },
    }

    print_header("RESUMEN MODELOS")
    print("Historical model metrics:")
    pprint(historical.get_metrics())
    print("\nLive model metrics:")
    pprint(live.get_metrics())
    print("\nManager mode actual:")
    print(manager.get_mode())
    print("Live samples:", manager.get_live_sample_count())

    for name, data in scenarios.items():
        print_header(f"ESCENARIO: {name}")

        print("\nInput:")
        pprint(data)

        hist_result = historical.predict(data)
        live_result = live.predict(data)
        manager_result = manager.predict(data)
        strategy_result = suggest_context_decision(data)

        print_result_block("HistoricalTradePredictor", hist_result)
        print_result_block("TradePredictor", live_result)
        print_result_block("TradePredictionManager", manager_result)
        print_result_block("StrategySuggestion", strategy_result)

        print("\nResumen corto:")
        print(
            f"- Historical: pred={hist_result.get('prediction')} "
            f"win={hist_result.get('probability_win', 0):.2%} "
            f"fallback={hist_result.get('fallback')}"
        )
        print(
            f"- Live:       pred={live_result.get('prediction')} "
            f"win={live_result.get('probability_win', 0):.2%} "
            f"fallback={live_result.get('fallback')}"
        )
        print(
            f"- Manager:    pred={manager_result.get('prediction')} "
            f"win={manager_result.get('probability_win', 0):.2%} "
            f"mode={manager_result.get('manager_mode')}"
        )
        print(
            f"- Strategy:   {strategy_result.get('strategy_suggestion')} | "
            f"Risk: {strategy_result.get('risk_suggestion')}"
        )

        # Guardar en log offline de IA
        log_ai_decision(
            scenario_name=name,
            input_data=data,
            historical_result=hist_result,
            live_result=live_result,
            manager_result=manager_result,
            strategy_result=strategy_result,
        )

    print_header("FIN TEST ESCENARIOS")
    print("Se guardaron resultados en ai_decision_log.csv")


if __name__ == "__main__":
    main()