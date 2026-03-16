import joblib

MODEL_FILE = "ai_model.pkl"

try:
    model = joblib.load(MODEL_FILE)
except:
    model = None


def predict_trade(rsi, ma50, ma200, volume):

    if model is None:
        return 1  # si no hay modelo todavía, permite operar

    features = [[rsi, ma50, ma200, volume]]

    prediction = model.predict(features)

    return prediction[0]