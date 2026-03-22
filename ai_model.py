import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib
import os

MODEL_FILE = "model.pkl"

import time

LAST_TRAIN = 0

def auto_train():

    global LAST_TRAIN

    now = time.time()

    # cada 5 minutos
    if now - LAST_TRAIN > 300:
        print("🧠 Reentrenando IA...")
        train_model()
        LAST_TRAIN = now


# =========================
# ENTRENAMIENTO IA
# =========================
def train_model():

    if not os.path.exists("trades_dataset.csv"):
        print("⚠ No hay dataset")
        return None

    df = pd.read_csv("trades_dataset.csv")

    if len(df) < 30:
        print("⚠ Muy pocos datos para entrenar")
        return None

    try:
        # =========================
        # CREAR FEATURES SI FALTAN
        # =========================

        if "ma50" not in df.columns or "price" not in df.columns:
            print("⚠ Faltan columnas base")
            return None

        # trend = tendencia alcista
        if "trend" not in df.columns:
            df["trend"] = (df["price"] > df["ma50"]).astype(int)

        # momentum = fuerza del movimiento
        if "momentum" not in df.columns:
            df["momentum"] = df["price"] - df["ma50"]

        # validaciones
        if "rsi" not in df.columns:
            print("⚠ Falta RSI")
            return None

        if "volume" not in df.columns:
            print("⚠ Falta volumen")
            return None

        if "result" not in df.columns:
            print("⚠ Falta result")
            return None

        # =========================
        # DATASET FINAL
        # =========================
        X = df[["rsi", "volume", "trend", "momentum"]]
        y = df["result"].astype(int)

        model = RandomForestClassifier(n_estimators=100)
        model.fit(X, y)

        joblib.dump(model, MODEL_FILE)

        print("✅ Modelo IA entrenado correctamente")

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
    """
    data = {
        rsi,
        volume,
        trend,
        momentum
    }
    """

    model = load_model()

    # =========================
    # IA REAL (si hay modelo)
    # =========================
    if model:
        try:
            X = [[
                data.get("rsi", 50),
                data.get("volume", 1),
                int(data.get("trend", 0)),
                data.get("momentum", 0)
            ]]

            pred = model.predict(X)[0]
            return int(pred)

        except Exception as e:
            print("⚠ Error modelo IA:", e)

    # =========================
    # FALLBACK INTELIGENTE
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