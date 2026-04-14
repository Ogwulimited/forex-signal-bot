"""
Anti-spam for trade signals – persists state across runs.
"""

import json
import os
from datetime import datetime, timedelta

STATE_FILE = "signal_state.json"
COOLDOWN_HOURS = 4  # Same signal (pair+direction) won't repeat within 4 hours

def _load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {}

def _save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def should_send_signal(pair, direction):
    """
    Returns True if the signal for this pair+direction should be sent.
    Checks cooldown period.
    """
    state = _load_state()
    key = f"{pair}_{direction}"
    last_sent = state.get(key)
    if last_sent:
        last_time = datetime.fromisoformat(last_sent)
        if datetime.now() - last_time < timedelta(hours=COOLDOWN_HOURS):
            return False
    return True

def mark_signal_sent(pair, direction):
    """Record that a signal was sent."""
    state = _load_state()
    key = f"{pair}_{direction}"
    state[key] = datetime.now().isoformat()
    _save_state(state)
