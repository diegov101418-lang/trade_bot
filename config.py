import json
import os
import threading
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, "bot_state.json")

bot_thread = None


# ===============================
# PROTECCIÓN HEDGE FUND
# ===============================

MAX_DRAWDOWN = 0.30        # 30% pérdida máxima total
MAX_DAILY_LOSS = 0.05      # 5% pérdida diaria
MAX_TRADES_PER_DAY = 20    # máximo operaciones por día
# ===============================
# GESTIÓN DE RIESGO
# ===============================
RISK_PER_TRADE = 0.02
MAX_POSITIONS = 5

# =========================
# STATE BOT
# =========================
STATE_FILE = "runtime_state.json"


def load_state():

    if not os.path.exists(STATE_FILE):
        data = {"running": False, "mode": "demo"}
        with open(STATE_FILE, "w") as f:
            json.dump(data, f)
        return data

    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save_state(data):

    with open(STATE_FILE, "w") as f:
        json.dump(data, f)


def is_running():
    return load_state().get("running", False)


def set_running(value):
    data = load_state()
    data["running"] = value
    save_state(data)


def get_mode():
    return load_state().get("mode", "demo")


def set_mode(mode):
    data = load_state()
    data["mode"] = mode
    save_state(data)

def ensure_state():

    if not os.path.exists(STATE_FILE):

        state = {
            "running": False,
            "mode": "demo"
        }

        with open(STATE_FILE, "w") as f:
            json.dump(state, f)


def read_state():

    ensure_state()

    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except:
        return {"running": False, "mode": "demo"}


def write_state(state):

    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


# =========================
# BOT CONTROL REAL (FIX)
# =========================
def start_bot():

    global bot_thread

    # 🔥 IMPORT LOCAL (EVITA LOOP)
    from bot import start_bot as run_bot_loop

    state = read_state()

    if state["running"]:
        print("⚠ Bot ya está corriendo")
        return

    state["running"] = True
    write_state(state)

    print("🚀 Iniciando BOT en background...")

    bot_thread = threading.Thread(target=run_bot_loop, daemon=True)
    bot_thread.start()


def stop_bot():

    # 🔥 IMPORT LOCAL (EVITA LOOP)
    from bot import stop_bot as stop_bot_loop

    state = read_state()

    state["running"] = False
    write_state(state)

    print("⛔ Deteniendo BOT...")

    try:
        stop_bot_loop()
    except Exception as e:
        print("Error deteniendo bot:", e)


def is_running():

    state = read_state()
    return state.get("running", False)


# =========================
# MODO
# =========================
def set_mode(mode):

    state = read_state()
    state["mode"] = mode
    write_state(state)

    print(f"🔄 Modo cambiado a: {mode}")


def get_mode():

    state = read_state()
    return state.get("mode", "demo")

# ===============================
# CONFIG OPTIMIZADA (IA)
# ===============================
OPTIMIZED_FILE = "optimized_config.json"


def save_best_config(data):

    with open(OPTIMIZED_FILE, "w") as f:
        json.dump(data, f)


def load_best_config():

    if not os.path.exists(OPTIMIZED_FILE):
        return None

    try:
        with open(OPTIMIZED_FILE, "r") as f:
            return json.load(f)
    except:
        return None