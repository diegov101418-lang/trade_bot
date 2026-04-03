import json
import os
import threading
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, "runtime_state.json")

STRATEGY = "auto"
bot_thread = None

# ===============================
# PROTECCIÓN HEDGE FUND
# ===============================
MAX_DRAWDOWN = 0.30
MAX_DAILY_LOSS = 0.05
MAX_TRADES_PER_DAY = 100

# ===============================
# RIESGO
# ===============================
RISK_PER_TRADE = 0.02
MAX_POSITIONS = 3

# =========================
# STATE
# =========================
def ensure_state():
    if not os.path.exists(STATE_FILE):
        with open(STATE_FILE, "w") as f:
            json.dump({"running": False, "mode": "demo"}, f)


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
# BOT CONTROL
# =========================
def is_running():
    return read_state().get("running", False)


def set_running(value):
    state = read_state()
    state["running"] = value
    write_state(state)


def get_mode():
    return read_state().get("mode", "demo")


def set_mode(mode):
    state = read_state()
    state["mode"] = mode
    write_state(state)
    print(f"🔄 Modo cambiado a: {mode}")


# =========================
# STRATEGY
# =========================
def set_strategy(name):
    global STRATEGY
    STRATEGY = name


def get_strategy_name():
    return STRATEGY


# ===============================
# CONFIG IA
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