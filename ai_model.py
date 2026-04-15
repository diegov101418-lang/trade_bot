import os
import time
import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier

MODEL_FILE = "model.pkl"
DATA_FILE = "trades_dataset_train.csv"
TARGET_COLUMN = "result_net"
LAST_TRAIN = 0

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
    "liquidity_mode_num",
    "ai_context_risk_num",
]


# =========================
# ENCODERS
# =========================
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


def encode_liquidity(value):
    value = str(value).lower().strip()
    if value == "low":
        return 0
    if value == "medium":
        return 1
    if value == "normal":
        return 2
    return 1


def encode_risk(value):
    value = str(value).lower().strip()
    if value == "conservative":
        return 0
    if value == "normal":
        return 1
    if value == "aggressive":
        return 2
    return 1


# =========================
# AUTO TRAIN
# =========================
def auto_train():
    global LAST_TRAIN

    now = time.time()
    if now - LAST_TRAIN > 300:
        print("🧠 Reentrenando IA principal...")
        train_model()
        LAST_TRAIN = now


# =========================
# PREPARE DATASET
# =========================
def prepare_dataset(df):
    required_cols = [
        "rsi",
        "volume",
        "trend",
        "momentum",
        "hour",
        "day_of_week",
        "signal_confidence",
        "market_regime",
        "atr",
        "volatility_context",
        "liquidity_mode",
        "ai_context_risk",
        TARGET_COLUMN,
    ]

    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        print(f"⚠ Faltan columnas en dataset IA: {missing}")
        return None

    df = df.copy()
    df = df.replace([np.inf, -np.inf], np.nan)

    df = df[df[TARGET_COLUMN].astype(str).str.strip() != ""]
    if df.empty:
        print("⚠ Dataset sin trades cerrados")
        return None

    numeric_cols = [
        "rsi",
        "volume",
        "trend",
        "momentum",
        "hour",
        "day_of_week",
        "signal_confidence",
        "atr",
        TARGET_COLUMN,
    ]

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["market_regime_num"] = df["market_regime"].apply(encode_market_regime)
    df["volatility_context_num"] = df["volatility_context"].apply(encode_volatility)
    df["liquidity_mode_num"] = df["liquidity_mode"].apply(encode_liquidity)
    df["ai_context_risk_num"] = df["ai_context_risk"].apply(encode_risk)

    df[TARGET_COLUMN] = pd.to_numeric(df[TARGET_COLUMN], errors="coerce")
    df = df[df[TARGET_COLUMN].isin([0, 1])]

    df = df.dropna(subset=FEATURES + [TARGET_COLUMN])

    if len(df) < 30:
        print("⚠ Dataset insuficiente tras limpieza")
        return None

    return df


# =========================
# ENTRENAMIENTO IA
# =========================
def train_model():
    if not os.path.exists(DATA_FILE):
        print("⚠ No hay dataset")
        return None

    try:
        df = pd.read_csv(DATA_FILE, encoding="utf-8", on_bad_lines="skip", engine="python")
    except Exception as e:
        print(f"⚠ Error leyendo dataset IA: {e}")
        return None

    if df.empty:
        print("⚠ Dataset vacío")
        return None

    df = prepare_dataset(df)
    if df is None:
        return None

    unique_results = sorted(df[TARGET_COLUMN].unique())
    if len(unique_results) < 2:
        print("⚠ Dataset sin suficiente variedad de resultados")
        return None

    try:
        X = df[FEATURES]
        y = df[TARGET_COLUMN].astype(int)

        model = RandomForestClassifier(
            n_estimators=200,
            max_depth=8,
            min_samples_leaf=3,
            random_state=42
        )
        model.fit(X, y)

        joblib.dump(model, MODEL_FILE)

        print(f"✅ Modelo IA principal entrenado | samples: {len(df)}")
        print("📊 Features usadas:", FEATURES)
        return model

    except Exception as e:
        print(f"🔥 Error entrenando modelo principal: {e}")
        return None


# =========================
# CARGAR MODELO
# =========================
def load_model():
    if not os.path.exists(MODEL_FILE):
        return train_model()

    try:
        return joblib.load(MODEL_FILE)
    except Exception:
        return train_model()


# =========================
# IA PRINCIPAL
# =========================
def predict_trade(data):
    model = load_model()

    if model:
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
                "liquidity_mode_num": encode_liquidity(data.get("liquidity_mode", "normal")),
                "ai_context_risk_num": encode_risk(data.get("ai_context_risk", "normal")),
            }])

            pred = model.predict(X)[0]
            return int(pred)

        except Exception as e:
            print(f"⚠ Error modelo IA principal: {e}")

    # =========================
    # FALLBACK
    # =========================
    score = 0

    if float(data.get("rsi", 50)) < 35:
        score += 1

    if float(data.get("volume", 1)) > 1:
        score += 1

    if int(data.get("trend", 0)) == 1:
        score += 1

    if float(data.get("momentum", 0)) > 0:
        score += 1

    if str(data.get("market_regime", "")).lower() == "bull":
        score += 1

    return 1 if score >= 3 else 0