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

DATASETS = [
    ("trades_dataset_v1.csv", "v1"),
    ("trades_dataset_v2.csv", "v2"),
    ("trades_dataset_v3.csv", "v3"),
]

OUTPUT_FILE = "trades_dataset_merged.csv"


def load_and_normalize_csv(filepath: str, version: str) -> pd.DataFrame | None:
    if not os.path.exists(filepath):
        print(f"⚠ No existe: {filepath}")
        return None

    try:
        df = pd.read_csv(filepath, encoding="utf-8", on_bad_lines="skip")
    except Exception as e:
        print(f"❌ Error leyendo {filepath}: {e}")
        return None

    # Agregar versión
    df["dataset_version"] = version

    # Crear columnas faltantes
    for col in COMMON_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    # Quedarse solo con columnas comunes
    df = df[COMMON_COLUMNS].copy()

    # Limpieza básica
    df = df.fillna("")

    return df


def main():
    frames = []

    for filepath, version in DATASETS:
        df = load_and_normalize_csv(filepath, version)
        if df is not None and len(df) > 0:
            print(f"✅ {filepath}: {len(df)} filas")
            frames.append(df)

    if not frames:
        print("❌ No se pudo cargar ningún dataset")
        return

    merged = pd.concat(frames, ignore_index=True)
    merged.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")

    print(f"\n✅ Dataset unificado generado: {OUTPUT_FILE}")
    print(f"📊 Total filas: {len(merged)}")
    print("\n📌 Filas por versión:")
    print(merged["dataset_version"].value_counts())


if __name__ == "__main__":
    main()