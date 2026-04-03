import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib
import os
import numpy as np
import time

MODEL_FILE = "model.pkl"
DATA_FILE = "trades_dataset.csv"
LAST_TRAIN = 0


# =========================
# AUTO TRAIN
# =========================
def auto_train():
    global LAST_TRAIN

    now = time.time()

    if now - LAST_TRAIN > 300:
        print("🧠 Reentrenando IA...")
        train_model()
        LAST_TRAIN = now


# =========================
# ENTRENAMIENTO IA
# =========================
def train_model():
    if not os.path.exists(DATA_FILE):
        print("⚠ No hay dataset")
        return None

    try:
        df = pd.read_csv( "build_training_dataset.py")
    except Exception as e:
        print(f"⚠ Error leyendo dataset IA: {e}")
        return None

    if df.empty:
        print("⚠ Dataset vacío")
        return None

    if len(df) < 30:
        print("⚠ Muy pocos datos para entrenar")
        return None

    try:
        # =========================
        # LIMPIEZA
        # =========================
        df = df.replace([np.inf, -np.inf], np.nan)

        required_cols = ["rsi", "volume", "trend", "momentum", "result"]

        for col in required_cols:
            if col not in df.columns:
                print(f"⚠ Falta columna: {col}")
                return None

        # eliminar filas sin resultado
        df = df[df["result"] != ""]

        if df.empty:
            print("⚠ Dataset sin trades cerrados")
            return None

        # convertir columnas a numérico
        df["rsi"] = pd.to_numeric(df["rsi"], errors="coerce")
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
        df["trend"] = pd.to_numeric(df["trend"], errors="coerce")
        df["momentum"] = pd.to_numeric(df["momentum"], errors="coerce")
        df["result"] = pd.to_numeric(df["result"], errors="coerce")

        # eliminar NaN
        df = df.dropna(subset=["rsi", "volume", "trend", "momentum", "result"])

        if len(df) < 30:
            print("⚠ Dataset insuficiente tras limpieza")
            return None

        # asegurar clases válidas
        unique_results = sorted(df["result"].unique())
        if len(unique_results) < 2:
            print("⚠ Dataset sin suficiente variedad de resultados")
            return None

        # =========================
        # DATASET FINAL
        # =========================
        X = df[["rsi", "volume", "trend", "momentum"]]
        y = df["result"].astype(int)

        model = RandomForestClassifier(
            n_estimators=100,
            random_state=42
        )
        model.fit(X, y)

        joblib.dump(model, MODEL_FILE)

        print(f"✅ Modelo IA entrenado | samples: {len(df)}")
        return model

    except Exception as e:
        print("🔥 Error entrenando modelo:", e)
        return None


# =========================
# CARGAR MODELO
# =========================
def load_model():
    if not os.path.exists(MODEL_FILE):
        return train_model()

    try:
        return joblib.load(MODEL_FILE)
    except:
        return train_model()


# =========================
# IA PRINCIPAL
# =========================
def predict_trade(data):
    model = load_model()

    # =========================
    # IA REAL
    # =========================
    if model:
        try:
            X = pd.DataFrame([{
                "rsi": float(data.get("rsi", 50)),
                "volume": float(data.get("volume", 1)),
                "trend": int(data.get("trend", 0)),
                "momentum": float(data.get("momentum", 0))
            }])

            pred = model.predict(X)[0]
            return int(pred)

        except Exception as e:
            print("⚠ Error modelo IA:", e)

    # =========================
    # FALLBACK
    # =========================
    score = 0

    if data.get("rsi", 50) < 35:
        score += 1

    if data.get("volume", 1) > 1:
        score += 1

    if data.get("trend", False):
        score += 1

    if data.get("momentum", 0) > 0:
        score += 1

    return 1 if score >= 3 else 0