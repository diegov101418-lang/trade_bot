from position_manager import get_open_positions
from indicators import get_indicators


FEE_RATE = 0.001  # 0.1% por lado


def sanitize_dict(d):
    return {str(k): v for k, v in d.items() if k is not None}


price_cache = {}

def get_live_positions():
    positions = get_open_positions()
    live_positions = []

    for pos in positions:
        enriched = dict(pos)

        try:
            symbol = pos["symbol"]

            if symbol in price_cache:
                last = price_cache[symbol]
            else:
                df = get_indicators(symbol)
                if df is None or len(df) == 0:
                    raise Exception("No data")

                last = df.iloc[-1]
                price_cache[symbol] = last

            current_price = float(last["close"])
            enriched["current_price"] = current_price

            entry = float(pos.get("entry_price", 0) or 0)
            qty = float(pos.get("quantity", 0) or 0)
            capital = float(pos.get("capital", entry * qty) or 0)

            side = pos.get("side", "long")

            if entry > 0 and qty > 0:
                if side == "long":
                    pnl_gross = (current_price - entry) * qty
                else:
                    pnl_gross = (entry - current_price) * qty

                pnl_pct = (pnl_gross / capital * 100) if capital > 0 else 0

                current_value = max(current_price * qty, 0)

                fee_entry_est = capital * FEE_RATE
                fee_exit_est = current_value * FEE_RATE
                fee_total_est = fee_entry_est + fee_exit_est

                pnl_net = pnl_gross - fee_total_est
            else:
                pnl_gross = 0
                pnl_pct = 0
                fee_entry_est = 0
                fee_exit_est = 0
                fee_total_est = 0
                pnl_net = 0

            enriched.update({
                "pnl": round(pnl_gross, 4),
                "pnl_gross": round(pnl_gross, 4),
                "pnl_net": round(pnl_net, 4),
                "pnl_pct": round(pnl_pct, 2),
                "fee_entry_est": round(fee_entry_est, 4),
                "fee_exit_est": round(fee_exit_est, 4),
                "fee_total_est": round(fee_total_est, 4),
                "is_profit": pnl_net > 0
            })

        except Exception as e:
            print(f"⚠ Error actualizando posición {pos.get('symbol')}: {e}")

        enriched = sanitize_dict(enriched)
        live_positions.append(enriched)

    return live_positions