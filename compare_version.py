import os
import pandas as pd

DATA_FILE = "trades_dataset.csv"
SPLIT_INDEX = 191  # trades 1-191 = antes | 192+ = después


def load_data():
    if not os.path.exists(DATA_FILE):
        print("❌ No existe trades_dataset.csv")
        return None

    try:
        df = pd.read_csv(DATA_FILE)
    except Exception as e:
        print(f"❌ Error leyendo CSV: {e}")
        return None

    if df.empty:
        print("❌ Dataset vacío")
        return None

    # solo trades cerrados
    if "result" not in df.columns:
        print("❌ Falta columna result")
        return None

    df = df[df["result"].astype(str).str.strip() != ""].copy()

    if df.empty:
        print("❌ No hay trades cerrados")
        return None

    # conversiones
    for col in ["result", "pnl", "rsi", "volume", "trend", "momentum"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "pnl" not in df.columns:
        df["pnl"] = 0.0

    df["pnl"] = df["pnl"].fillna(0.0)
    df = df.dropna(subset=["result"])

    return df.reset_index(drop=True)


def summarize(df, label="TRAMO", initial_balance=1000):
    total = len(df)
    wins = int((df["result"] == 1).sum())
    losses = int((df["result"] == 0).sum())
    winrate = (wins / total * 100) if total > 0 else 0

    pnl = df["pnl"].fillna(0.0)
    gross_profit = pnl[pnl > 0].sum()
    gross_loss = pnl[pnl < 0].sum()
    net = pnl.sum()
    avg_trade = net / total if total > 0 else 0

    # equity + drawdown del tramo
    equity = initial_balance + pnl.cumsum()
    if len(equity) > 0:
        peak = equity.iloc[0]
    else:
        peak = initial_balance

    max_dd = 0.0
    for val in equity:
        if val > peak:
            peak = val
        dd = ((val - peak) / peak) * 100 if peak != 0 else 0
        if dd < max_dd:
            max_dd = dd

    return {
        "label": label,
        "trades": total,
        "wins": wins,
        "losses": losses,
        "winrate": round(winrate, 2),
        "gross_profit": round(float(gross_profit), 4),
        "gross_loss": round(float(gross_loss), 4),
        "net": round(float(net), 4),
        "avg_trade": round(float(avg_trade), 4),
        "max_drawdown": round(float(max_dd), 2),
    }


def print_summary(stats):
    print(f"\n=== {stats['label']} ===")
    print(f"Trades: {stats['trades']}")
    print(f"Wins: {stats['wins']}")
    print(f"Losses: {stats['losses']}")
    print(f"Winrate: {stats['winrate']}%")
    print(f"Ganancia bruta: {stats['gross_profit']}")
    print(f"Pérdida bruta: {stats['gross_loss']}")
    print(f"Profit neto: {stats['net']}")
    print(f"Profit por trade: {stats['avg_trade']}")
    print(f"Max drawdown: {stats['max_drawdown']}%")


def compare(before_stats, after_stats):
    print("\n=== COMPARACIÓN ===")

    diff_winrate = after_stats["winrate"] - before_stats["winrate"]
    diff_net = after_stats["net"] - before_stats["net"]
    diff_avg = after_stats["avg_trade"] - before_stats["avg_trade"]
    diff_dd = after_stats["max_drawdown"] - before_stats["max_drawdown"]

    print(f"Diferencia winrate: {diff_winrate:+.2f}%")
    print(f"Diferencia profit neto: {diff_net:+.4f}")
    print(f"Diferencia profit por trade: {diff_avg:+.4f}")
    print(f"Diferencia drawdown: {diff_dd:+.2f}%")

    print("\n=== LECTURA RÁPIDA ===")

    if after_stats["avg_trade"] > before_stats["avg_trade"]:
        print("✔ Mejoró el profit por trade")
    else:
        print("❌ No mejoró el profit por trade")

    if after_stats["net"] > before_stats["net"]:
        print("✔ Mejoró el resultado neto del tramo")
    else:
        print("❌ No mejoró el resultado neto del tramo")

    if after_stats["max_drawdown"] > before_stats["max_drawdown"]:
        print("✔ Mejoró el drawdown (menos negativo)")
    else:
        print("❌ No mejoró el drawdown")

    if after_stats["winrate"] > before_stats["winrate"]:
        print("✔ Mejoró el winrate")
    else:
        print("❌ No mejoró el winrate")


def main():
    df = load_data()
    if df is None:
        return

    total_closed = len(df)

    if total_closed <= SPLIT_INDEX:
        print(f"❌ No hay suficientes trades cerrados para comparar con corte {SPLIT_INDEX}")
        print(f"Trades cerrados actuales: {total_closed}")
        return

    df_before = df.iloc[:SPLIT_INDEX].copy()
    df_after = df.iloc[SPLIT_INDEX:].copy()

    before_stats = summarize(df_before, label=f"ANTES (1-{SPLIT_INDEX})")
    after_stats = summarize(df_after, label=f"DESPUÉS ({SPLIT_INDEX+1}-{total_closed})")

    print_summary(before_stats)
    print_summary(after_stats)
    compare(before_stats, after_stats)


if __name__ == "__main__":
    main()