import os
import pandas as pd

COMMON_COLUMNS = [
    "symbol",
    "rsi",
    "volume",
    "trend",
    "momentum",
    "result",
    "pnl",
    "timestamp",
    "hour",
    "day_of_week",
    "signal_confidence",
    "market_regime",
    "strategy_name",
    "risk_mode",
    "atr",
    "volatility_context",
    "market_session",
    "is_holiday_us",
    "holiday_name_us",
    "mfe_pct",
    "mae_pct",
    "dataset_version",
]

HISTORICAL_FILE = "trades_dataset_merged.csv"
LIVE_FILE = "trades_dataset.csv"
OUTPUT_FILE = "trades_dataset_train.csv"


def load_normalized(filepath: str, version_name: str) -> pd.DataFrame | None:
    if not os.path.exists(filepath):
        print(f"⚠ No existe: {filepath}")
        return None

    try:
        df = pd.read_csv(filepath, encoding="utf-8", on_bad_lines="skip")
    except Exception as e:
        print(f"❌ Error leyendo {filepath}: {e}")
        return None

    if "dataset_version" not in df.columns:
        df["dataset_version"] = version_name

    for col in COMMON_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    df = df[COMMON_COLUMNS].copy()
    df = df.fillna("")

    return df


def main():
    frames = []

    historical_df = load_normalized(HISTORICAL_FILE, "historical")
    if historical_df is not None and len(historical_df) > 0:
        frames.append(historical_df)

    live_df = load_normalized(LIVE_FILE, "live")
    if live_df is not None and len(live_df) > 0:
        frames.append(live_df)

    if not frames:
        print("❌ No hay datasets para combinar")
        return

    df = pd.concat(frames, ignore_index=True)

    # opcional: quitar duplicados aproximados
    df = df.drop_duplicates(
        subset=["symbol", "timestamp", "result", "pnl"],
        keep="last"
    )

    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")

    print(f"✅ Dataset de entrenamiento creado: {OUTPUT_FILE}")
    print(f"📊 Filas totales: {len(df)}")
    print(df["dataset_version"].value_counts())


if __name__ == "__main__":
    main()