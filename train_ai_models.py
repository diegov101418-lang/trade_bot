from ai_strategy_learner import train_strategy_models
from ai_model import train_model

if __name__ == "__main__":
    print("🧠 Entrenando modelo principal (buy/sell)...")
    train_model()

    print("🧠 Entrenando selector de estrategia + riesgo...")
    train_strategy_models("trades_dataset_train.csv")

    print("✅ Todo el sistema IA actualizado")