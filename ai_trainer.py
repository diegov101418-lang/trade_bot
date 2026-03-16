import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib

DATASET_FILE = "trades_dataset.csv"
MODEL_FILE = "ai_model.pkl"


def train_model():

    try:
        data = pd.read_csv(DATASET_FILE)
    except:
        print("No existe dataset")