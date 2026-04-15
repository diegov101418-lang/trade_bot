import os
import pandas as pd
import numpy as np
import joblib

from sklearn.ensemble import RandomForestClassifier

FEATURES = [
    "rsi",
    "volume",
    "trend",
    "momentum",
    "hour",
    "day_of_week",
    "signal_confidence",
    "market_regime_num",
    "atr",
    "volatility_context_num",
]

TARGET_STRATEGY = "strategy_name"
TARGET_RISK = "risk_mode"


def encode_market_regime(value):
    value = str(value).lower().strip()
    if value == "bull":
        return 1
    if value == "bear":
        return -1
    return 0


def encode_volatility(value):
    value = str(value).lower().strip()
    if value == "low":
        return 0
    if value == "medium":
        return 1
    if value == "high":
        return 2
    return 1


def load_dataset(file="trades_dataset_train.csv"):
    if not os.path.exists(file):
        print("⚠ No hay dataset")
        return None

    try:
        df = pd.read_csv(file, encoding="utf-8", on_bad_lines="skip", engine="python")
        return df
    except Exception as e:
        print(f"⚠ Error leyendo dataset: {e}")
        return None


def prepare_dataset(df):
    required = [
        "rsi",
        "volume",
        "trend",
        "momentum",
        "hour",
        "day_of_week",
        "signal_confidence",
        "atr",
        "market_regime",
        "volatility_context",
        TARGET_STRATEGY,
        TARGET_RISK,
        "result",
    ]

    missing = [c for c in required if c not in df.columns]
    if missing:
        print(f"⚠ Faltan columnas: {missing}")
        return None

    df = df.copy()
    df = df.replace([np.inf, -np.inf], np.nan)

    df = df[df["result"].astype(str).str.strip() != ""]
    df = df[df[TARGET_STRATEGY].astype(str).str.strip() != ""]
    df = df[df[TARGET_RISK].astype(str).str.strip() != ""]

    numeric_cols = [
        "rsi",
        "volume",
        "trend",
        "momentum",
        "hour",
        "day_of_week",
        "signal_confidence",
        "atr",
        "result",
    ]

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["market_regime_num"] = df["market_regime"].apply(encode_market_regime)
    df["volatility_context_num"] = df["volatility_context"].apply(encode_volatility)

    df = df[df["result"].isin([0, 1])]

    df = df.dropna(subset=FEATURES + [TARGET_STRATEGY, TARGET_RISK])

    return df


def train_strategy_models(file="trades_dataset_train.csv"):
    df = load_dataset(file)
    if df is None:
        return None, None

    df = prepare_dataset(df)
    if df is None or len(df) < 80:
        print("⚠ Muy pocos datos para entrenar strategy learner")
        return None, None

    print(f"📊 Filas válidas para entrenar: {len(df)}")

    X = df[FEATURES]

    y_strategy = df[TARGET_STRATEGY].astype(str)
    y_risk = df[TARGET_RISK].astype(str)

    strategy_model = None
    risk_model = None

    print("📈 strategy_name únicos:", sorted(y_strategy.unique()))
    print("⚙ risk_mode únicos:", sorted(y_risk.unique()))

    if y_strategy.nunique() < 2:
        print("⚠ Aún no hay variedad suficiente en strategy_name")
    else:
        strategy_model = RandomForestClassifier(
            n_estimators=200,
            max_depth=8,
            min_samples_leaf=3,
            random_state=42
        )
        strategy_model.fit(X, y_strategy)
        joblib.dump(strategy_model, "strategy_selector.pkl")
        print("✅ Strategy selector entrenado")

    if y_risk.nunique() < 2:
        print("⚠ Aún no hay variedad suficiente en risk_mode")
    else:
        risk_model = RandomForestClassifier(
            n_estimators=200,
            max_depth=8,
            min_samples_leaf=3,
            random_state=42
        )
        risk_model.fit(X, y_risk)
        joblib.dump(risk_model, "risk_selector.pkl")
        print("✅ Risk selector entrenado")

    return strategy_model, risk_model


def suggest_context_decision(data):
    result = {
        "strategy_suggestion": None,
        "risk_suggestion": None,
    }

    try:
        X = pd.DataFrame([{
            "rsi": float(data.get("rsi", 50)),
            "volume": float(data.get("volume", 1)),
            "trend": int(data.get("trend", 0)),
            "momentum": float(data.get("momentum", 0)),
            "hour": int(data.get("hour", 0)),
            "day_of_week": int(data.get("day_of_week", 0)),
            "signal_confidence": float(data.get("signal_confidence", 0)),
            "market_regime_num": encode_market_regime(data.get("market_regime", "sideways")),
            "atr": float(data.get("atr", 0)),
            "volatility_context_num": encode_volatility(data.get("volatility_context", "medium")),
        }])

        if os.path.exists("strategy_selector.pkl"):
            strategy_model = joblib.load("strategy_selector.pkl")
            result["strategy_suggestion"] = strategy_model.predict(X)[0]

        if os.path.exists("risk_selector.pkl"):
            risk_model = joblib.load("risk_selector.pkl")
            result["risk_suggestion"] = risk_model.predict(X)[0]

    except Exception as e:
        print(f"⚠ Error sugiriendo contexto IA: {e}")

    return result