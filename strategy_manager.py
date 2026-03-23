from strategies.trend import trend_strategy
from strategies.mean_reversion import mean_reversion_strategy
from strategies.breakout import breakout_strategy
from strategies.scalping import scalping_strategy


def evaluate_strategies(data):
    """
    data = indicadores del mercado
    devuelve lista de señales
    """

    signals = []

    strategies = [
        trend_strategy,
        mean_reversion_strategy,
        breakout_strategy,
        scalping_strategy
    ]

    for strat in strategies:
        try:
            signal = strat(data)
            if signal:
                signals.append(signal)
        except Exception as e:
            print(f"⚠ Error estrategia {strat.__name__}: {e}")

    return signals