import os
import pandas as pd
import matplotlib.pyplot as plt

DATA_FILE = "trades_dataset.csv"
OUTPUT_DIR = "analysis_reports"


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

    if "result" in df.columns:
        df = df[df["result"].astype(str).str.strip() != ""].copy()

    if df.empty:
        print("❌ No hay trades cerrados")
        return None

    for col in ["rsi", "volume", "trend", "momentum", "result", "pnl"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "pnl" in df.columns:
        df["pnl"] = df["pnl"].fillna(0)

    df = df.dropna(subset=["result"])
    return df


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def save_equity_curve(df):
    if "pnl" not in df.columns:
        return

    equity = 1000 + df["pnl"].cumsum()

    plt.figure(figsize=(10, 5))
    plt.plot(equity.values)
    plt.title("Equity Curve")
    plt.xlabel("Trade")
    plt.ylabel("Balance")
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "equity_curve.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"✅ Guardado: {path}")


def save_pnl_distribution(df):
    if "pnl" not in df.columns:
        return

    plt.figure(figsize=(10, 5))
    plt.hist(df["pnl"], bins=30)
    plt.title("Distribución de PnL por trade")
    plt.xlabel("PnL")
    plt.ylabel("Frecuencia")
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "pnl_distribution.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"✅ Guardado: {path}")


def save_symbol_performance(df):
    if "symbol" not in df.columns or "pnl" not in df.columns:
        return

    g = (
        df.groupby("symbol")["pnl"]
        .sum()
        .sort_values(ascending=False)
    )

    top = g.head(10)
    bottom = g.tail(10)

    plt.figure(figsize=(10, 6))
    top.sort_values().plot(kind="barh")
    plt.title("Top 10 símbolos por Net PnL")
    plt.xlabel("Net PnL")
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "top_symbols.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"✅ Guardado: {path}")

    plt.figure(figsize=(10, 6))
    bottom.sort_values().plot(kind="barh")
    plt.title("Bottom 10 símbolos por Net PnL")
    plt.xlabel("Net PnL")
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "bottom_symbols.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"✅ Guardado: {path}")


def save_rsi_analysis(df):
    if "rsi" not in df.columns or "pnl" not in df.columns:
        return

    bins = [0, 20, 30, 40, 50, 60, 70, 100]
    labels = ["0-20", "20-30", "30-40", "40-50", "50-60", "60-70", "70-100"]

    temp = df.copy()
    temp["rsi_range"] = pd.cut(temp["rsi"], bins=bins, labels=labels, include_lowest=True)

    g = temp.groupby("rsi_range", observed=False)["pnl"].sum()

    plt.figure(figsize=(10, 5))
    g.plot(kind="bar")
    plt.title("Net PnL por rango RSI")
    plt.xlabel("Rango RSI")
    plt.ylabel("Net PnL")
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "rsi_ranges.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"✅ Guardado: {path}")


def save_trend_analysis(df):
    if "trend" not in df.columns or "pnl" not in df.columns:
        return

    g = df.groupby("trend")["pnl"].sum()
    g.index = ["Bajista" if x == 0 else "Alcista" for x in g.index]

    plt.figure(figsize=(8, 5))
    g.plot(kind="bar")
    plt.title("Net PnL por tendencia")
    plt.xlabel("Tendencia")
    plt.ylabel("Net PnL")
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "trend_analysis.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"✅ Guardado: {path}")


def save_summary_csv(df):
    total = len(df)
    wins = int((df["result"] == 1).sum())
    losses = int((df["result"] == 0).sum())
    winrate = (wins / total * 100) if total > 0 else 0
    net_profit = df["pnl"].sum() if "pnl" in df.columns else 0
    avg_trade = net_profit / total if total > 0 else 0
    gross_profit = df.loc[df["pnl"] > 0, "pnl"].sum() if "pnl" in df.columns else 0
    gross_loss = df.loc[df["pnl"] < 0, "pnl"].sum() if "pnl" in df.columns else 0

    summary = pd.DataFrame([{
        "trades": total,
        "wins": wins,
        "losses": losses,
        "winrate_pct": round(winrate, 2),
        "gross_profit": round(gross_profit, 4),
        "gross_loss": round(gross_loss, 4),
        "net_profit": round(net_profit, 4),
        "avg_profit_per_trade": round(avg_trade, 4),
    }])

    path = os.path.join(OUTPUT_DIR, "summary.csv")
    summary.to_csv(path, index=False)
    print(f"✅ Guardado: {path}")


def main():
    df = load_data()
    if df is None:
        return

    ensure_output_dir()
    save_summary_csv(df)
    save_equity_curve(df)
    save_pnl_distribution(df)
    save_symbol_performance(df)
    save_rsi_analysis(df)
    save_trend_analysis(df)

    print(f"\n📁 Reporte generado en: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()