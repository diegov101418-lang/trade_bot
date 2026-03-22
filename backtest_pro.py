from binance.client import Client
import pandas as pd
from config import API_KEY, API_SECRET

client = Client(API_KEY, API_SECRET)


# =========================
# DATOS HISTÓRICOS
# =========================

def get_historical_data(symbol):

    klines = client.get_historical_klines(
        symbol,
        Client.KLINE_INTERVAL_5MINUTE,
        "30 days ago UTC"
    )

    df = pd.DataFrame(klines)

    df["close"] = df[4].astype(float)
    df["volume"] = df[5].astype(float)

    return df


# =========================
# INDICADORES REALES
# =========================

def add_indicators(df):

    df["ma50"] = df["close"].rolling(50).mean()

    delta = df["close"].diff()

    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()

    rs = gain / loss

    df["rsi"] = 100 - (100 / (1 + rs))

    return df


# =========================
# BACKTEST PRO
# =========================

def run_backtest(symbol):

    df = get_historical_data(symbol)
    df = add_indicators(df)

    balance = 1000
    position = 0
    entry_price = 0

    trades = []

    FEE = 0.001  # 0.1%
    TP = 0.03
    SL = -0.02

    for i in range(60, len(df)):

        row = df.iloc[i]

        price = row["close"]
        ma50 = row["ma50"]
        rsi = row["rsi"]

        # ================= BUY =================
        if position == 0:

            if price > ma50 and rsi < 35:

                position = (balance * (1 - FEE)) / price
                entry_price = price
                balance = 0

                trades.append({
                    "type": "BUY",
                    "price": price
                })

        # ================= SELL =================
        else:

            profit = (price - entry_price) / entry_price

            if profit >= TP or profit <= SL:

                balance = position * price * (1 - FEE)
                position = 0

                trades.append({
                    "type": "SELL",
                    "price": price,
                    "pnl": profit
                })

    if position > 0:
        balance = position * price

    # ================= MÉTRICAS =================

    wins = sum(1 for t in trades if t.get("pnl", 0) > 0)
    losses = sum(1 for t in trades if t.get("pnl", 0) <= 0)

    total = wins + losses
    winrate = (wins / total * 100) if total > 0 else 0

    return {
        "balance": balance,
        "trades": len(trades),
        "winrate": round(winrate, 2),
        "wins": wins,
        "losses": losses
    }

def run_backtest_custom(symbol, rsi_limit, tp, sl):

    df = get_historical_data(symbol)
    df = add_indicators(df)

    balance = 1000
    position = 0
    entry_price = 0

    trades = []

    FEE = 0.001

    for i in range(60, len(df)):

        row = df.iloc[i]

        price = row["close"]
        ma50 = row["ma50"]
        rsi = row["rsi"]

        # BUY
        if position == 0:

            if price > ma50 and rsi < rsi_limit:

                position = (balance * (1 - FEE)) / price
                entry_price = price
                balance = 0

        # SELL
        else:

            profit = (price - entry_price) / entry_price

            if profit >= tp or profit <= sl:

                balance = position * price * (1 - FEE)
                position = 0

                trades.append(profit)

    if position > 0:
        balance = position * price

    wins = sum(1 for t in trades if t > 0)
    total = len(trades)

    winrate = (wins / total * 100) if total > 0 else 0

    return {
        "balance": balance,
        "winrate": round(winrate, 2)
    }

# =========================
# RUN
# =========================

if __name__ == "__main__":

    symbol = "BTCUSDT"

    result = run_backtest(symbol)

    print("\n📊 RESULTADO BACKTEST")
    print("Balance final:", result["balance"])
    print("Trades:", result["trades"])
    print("Winrate:", result["winrate"], "%")
    print("Ganadas:", result["wins"])
    print("Perdidas:", result["losses"])