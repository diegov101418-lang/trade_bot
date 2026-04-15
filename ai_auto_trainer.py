import os
import time
import subprocess
import pandas as pd

LAST_TRAIN_FILE = "last_ai_train.txt"
TRAIN_DATASET = "trades_dataset_train.csv"
LIVE_DATASET = "trades_dataset.csv"

MIN_NEW_CLOSED_TRADES = 20
MIN_TOTAL_TRAIN_ROWS = 80
RETRAIN_INTERVAL_SECONDS = 60 * 60 * 3   # cada 3 horas


def get_now_ts():
    return int(time.time())


def load_last_train_info():
    if not os.path.exists(LAST_TRAIN_FILE):
        return {"timestamp": 0, "closed_trades": 0}

    try:
        with open(LAST_TRAIN_FILE, "r", encoding="utf-8") as f:
            raw = f.read().strip().split("|")
            return {
                "timestamp": int(raw[0]),
                "closed_trades": int(raw[1]),
            }
    except Exception:
        return {"timestamp": 0, "closed_trades": 0}


def save_last_train_info(timestamp, closed_trades):
    with open(LAST_TRAIN_FILE, "w", encoding="utf-8") as f:
        f.write(f"{int(timestamp)}|{int(closed_trades)}")


def count_closed_trades(csv_file):
    if not os.path.exists(csv_file):
        return 0

    try:
        df = pd.read_csv(csv_file, encoding="utf-8", on_bad_lines="skip", engine="python")
    except Exception as e:
        print(f"⚠ Error leyendo {csv_file}: {e}")
        return 0

    if "result" not in df.columns:
        return 0

    return int((df["result"].astype(str).str.strip() != "").sum())


def count_rows(csv_file):
    if not os.path.exists(csv_file):
        return 0

    try:
        df = pd.read_csv(csv_file, encoding="utf-8", on_bad_lines="skip", engine="python")
        return len(df)
    except Exception as e:
        print(f"⚠ Error contando filas en {csv_file}: {e}")
        return 0


def rebuild_training_dataset():
    print("🧱 Reconstruyendo dataset de entrenamiento...")
    subprocess.run(["python", "build_training_dataset.py"], check=False)


def train_ai_models():
    print("🧠 Reentrenando IA...")
    subprocess.run(["python", "train_ai_models.py"], check=False)


def maybe_retrain():
    info = load_last_train_info()
    now_ts = get_now_ts()

    if now_ts - info["timestamp"] < RETRAIN_INTERVAL_SECONDS:
        return

    current_closed = count_closed_trades(LIVE_DATASET)
    new_closed = current_closed - info["closed_trades"]

    if new_closed < MIN_NEW_CLOSED_TRADES:
        print(f"⏳ Aún no hay suficientes trades nuevos para reentrenar ({new_closed}/{MIN_NEW_CLOSED_TRADES})")
        return

    rebuild_training_dataset()

    total_rows = count_rows(TRAIN_DATASET)
    if total_rows < MIN_TOTAL_TRAIN_ROWS:
        print(f"⚠ Dataset de entrenamiento aún chico ({total_rows}/{MIN_TOTAL_TRAIN_ROWS})")
        return

    train_ai_models()
    save_last_train_info(now_ts, current_closed)
    print("✅ Reentrenamiento automático completado")