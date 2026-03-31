from position_manager import get_open_positions
from indicators import get_indicators


def sanitize_dict(d):
    return {str(k): v for k, v in d.items() if k is not None}


def get_live_positions():
    positions = get_open_positions()
    live_positions = []

    for pos in positions:
        enriched = dict(pos)

        try:
            symbol = pos["symbol"]
            df = get_indicators(symbol)

            if df is not None and len(df) > 0:
                last = df.iloc[-1]
                current_price = float(last["close"])
                enriched["current_price"] = current_price

                entry = float(pos.get("entry_price", 0) or 0)
                qty = float(pos.get("quantity", 0) or 0)

                if entry > 0 and qty > 0:
                    pnl = (current_price - entry) * qty
                    pnl_pct = ((current_price - entry) / entry) * 100
                else:
                    pnl = 0
                    pnl_pct = 0

                enriched["pnl"] = round(pnl, 4)
                enriched["pnl_pct"] = round(pnl_pct, 2)
            else:
                enriched["current_price"] = None
                enriched["pnl"] = 0
                enriched["pnl_pct"] = 0

        except Exception as e:
            print(f"⚠ Error actualizando posición {pos.get('symbol')}: {e}")
            enriched["current_price"] = None
            enriched["pnl"] = 0
            enriched["pnl_pct"] = 0

        enriched = sanitize_dict(enriched)
        live_positions.append(enriched)

    return live_positions