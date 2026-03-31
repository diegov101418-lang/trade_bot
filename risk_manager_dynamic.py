import json
import os

STATE_FILE = "risk_state.json"

# valores base
BASE_RISK = 0.02
MIN_RISK = 0.005
MAX_RISK = 0.03


def load_state():
    if not os.path.exists(STATE_FILE):
        return {
            "risk": BASE_RISK,
            "mode": "normal"
        }

    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


# =========================
# AJUSTE AUTOMÁTICO
# =========================
def adjust_risk(winrate, drawdown):

    state = load_state()
    risk = state["risk"]

    print(f"🧠 Ajustando riesgo | WR:{winrate:.2f} DD:{drawdown:.2f}")

    # 🔴 modo peligro
    if drawdown < -3:
        risk *= 0.7
        state["mode"] = "defensive"

    # 🟡 rendimiento bajo
    elif winrate < 0.35:
        risk *= 0.8
        state["mode"] = "caution"

    # 🟢 buen rendimiento
    elif winrate > 0.42:
        risk *= 1.1
        state["mode"] = "aggressive"

    else:
        state["mode"] = "normal"

    # límites
    risk = max(MIN_RISK, min(MAX_RISK, risk))

    state["risk"] = round(risk, 4)

    save_state(state)

    print(f"⚙ Nuevo riesgo: {state['risk']} | modo: {state['mode']}")

    return state["risk"]


# =========================
# GET ACTUAL
# =========================
def get_current_risk():
    state = load_state()
    return state["risk"]