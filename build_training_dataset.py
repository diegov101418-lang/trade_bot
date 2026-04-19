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
    "holiday_name_us",
    "mfe_pct",
    "mae_pct",
    "result_net",
    "dataset_version",
    "is_holiday_ar",
    "holiday_name_ar",
    "is_holiday_eu",
    "holiday_name_eu",
    "is_holiday_asia",
    "holiday_name_asia",
    "is_good_friday",
    "is_holiday_us",
    "risk_per_trade_used",
    "liquidity_mode",
    "ai_trade_decision",
    "ai_context_risk",
    "trade_filter_reason",
    "prob_live",
    "prob_historical",
    "prob_final",
    "decision_source",
    "models_agree",
    "shadow_prediction",
    "pnl_net",
    "result_net",
]

HISTORICAL_FILE = "trades_dataset_merged.csv"
LIVE_FILE = "trades_dataset.csv"
OUTPUT_FILE = "trades_dataset_train.csv"


def load_normalized(filepath: str, version_name: str) -> pd.DataFrame | None:
    if not os.path.exists(filepath):
        print(f"⚠ No existe: {filepath}")
        return None

    try:
        df = pd.read_csv(filepath, encoding="utf-8", on_bad_lines="skip", engine="python")
    except Exception as e:
        print(f"❌ Error leyendo {filepath}: {e}")
        return None

    if df.empty:
        print(f"⚠ Dataset vacío: {filepath}")
        return None

    if "dataset_version" not in df.columns:
        df["dataset_version"] = version_name

    for col in COMMON_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    df = df[COMMON_COLUMNS].copy()
    df = df.fillna("")

    return df


def clean_and_prepare(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # dejar solo trades cerrados
    df = df[df["result"].astype(str).str.strip() != ""]

    # normalizar campos críticos
    for col in ["timestamp", "pnl", "rsi", "volume", "momentum", "atr", "signal_confidence"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # quitar duplicados
    df = df.drop_duplicates(
        subset=["symbol", "timestamp", "result", "pnl"],
        keep="last"
    )

    # ordenar por tiempo si existe
    if "timestamp" in df.columns:
        df = df.sort_values(by="timestamp", na_position="last")

    return df


def print_summary(df: pd.DataFrame):
    print(f"✅ Dataset de entrenamiento creado: {OUTPUT_FILE}")
    print(f"📊 Filas totales: {len(df)}")

    if "dataset_version" in df.columns:
        print("📦 Versiones:")
        print(df["dataset_version"].value_counts(dropna=False))

    if "strategy_name" in df.columns:
        valid_strategy = df["strategy_name"].astype(str).str.strip()
        print("🧠 Estrategias:")
        print(valid_strategy[valid_strategy != ""].value_counts().head(10))

    if "risk_mode" in df.columns:
        valid_risk = df["risk_mode"].astype(str).str.strip()
        print("⚙ Risk modes:")
        print(valid_risk[valid_risk != ""].value_counts().head(10))

    if "result" in df.columns:
        print("🎯 Resultados:")
        print(df["result"].astype(str).value_counts())


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
    df = clean_and_prepare(df)

    if df.empty:
        print("❌ El dataset combinado quedó vacío después de limpiar")
        return

    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")
    print_summary(df)


if __name__ == "__main__":
    main()