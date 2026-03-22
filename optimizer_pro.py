from backtest_pro import run_backtest_custom


def optimize(symbol):

    best_result = None

    # rangos a probar
    rsi_values = [25, 30, 35, 40]
    tp_values = [0.02, 0.03, 0.04, 0.05]
    sl_values = [-0.01, -0.02, -0.03]

    for rsi_limit in rsi_values:
        for tp in tp_values:
            for sl in sl_values:

                result = run_backtest_custom(
                    symbol,
                    rsi_limit,
                    tp,
                    sl
                )

                score = result["balance"]

                print(f"Test RSI:{rsi_limit} TP:{tp} SL:{sl} → {score}")

                if best_result is None or score > best_result["score"]:

                    best_result = {
                        "rsi": rsi_limit,
                        "tp": tp,
                        "sl": sl,
                        "score": score,
                        "winrate": result["winrate"]
                    }
                    from config import save_best_config
    save_best_config(best_result)
    return best_result