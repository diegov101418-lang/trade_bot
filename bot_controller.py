import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

STATE_FILE = os.path.join(BASE_DIR, "bot_state.json")

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


def start_bot():

    state = read_state()
    state["running"] = True
    write_state(state)


def stop_bot():

    state = read_state()
    state["running"] = False
    write_state(state)


def is_running():

    state = read_state()
    return state.get("running", False)


def set_mode(mode):

    state = read_state()
    state["mode"] = mode
    write_state(state)


def get_mode():

    state = read_state()
    return state.get("mode", "demo")