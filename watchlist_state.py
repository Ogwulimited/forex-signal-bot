import json
import os

STATE_FILE = "watchlist_state.json"

def load_watchlist_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_watchlist_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def should_send_watchlist_alert(pair, direction):
    state = load_watchlist_state()
    last_direction = state.get(pair)

    if last_direction == direction:
        return False

    state[pair] = direction
    save_watchlist_state(state)
    return True
