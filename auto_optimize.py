import time
from optimizer_pro import optimize

while True:

    print("🧠 Re-optimizando estrategia...")

    optimize("BTCUSDT")

    print("✅ Nueva config guardada")

    time.sleep(60 * 60 * 6)  # cada 6 horas