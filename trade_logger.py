"""
Trade Logger – Records every signal to trades.json for later analysis.
"""
import json
import os
from datetime import datetime

TRADES_FILE = "trades.json"

def get_session():
    """Return a trading session label based on UTC hour."""
    hour = datetime.utcnow().hour
    if 7 <= hour < 16:
        return "London"
    elif 12 <= hour < 20:
        return "New York"
    elif 0 <= hour < 7:
        return "Asian"
    else:
        return "Other"

def log_trade(signal, bias_data, breakout, rejection, sweep, direction):
    """
    Append a new trade record to trades.json.
    signal: dict from signal_dispatcher (pair, direction, entry, sl, tp, timeframe, rr)
    bias_data: dict from get_mtf_bias()
    breakout: dict from detect_breakout
    rejection: dict from detect_rejection
    sweep: dict from detect_liquidity_sweep
    direction: 'buy' or 'sell'
    """
    # Load existing trades
    trades = []
    if os.path.exists(TRADES_FILE):
        with open(TRADES_FILE, 'r') as f:
            try:
                trades = json.load(f)
            except json.JSONDecodeError:
                trades = []

    # Build trade record
    trade = {
        "id": f"{signal['pair']}_{signal['direction']}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
        "pair": signal['pair'],
        "direction": signal['direction'],
        "entry": signal['entry'],
        "sl": signal['sl'],
        "tp": signal['tp'],
        "rr": signal['rr'],
        "timeframe": signal.get('timeframe', '5M'),
        "timestamp": datetime.utcnow().isoformat(),
        "session": get_session(),
        "day_of_week": datetime.utcnow().strftime('%A'),
        "bias_4h": bias_data.get('bias_4h', 'unknown'),
        "bias_1h": bias_data.get('bias_1h', 'unknown'),
        "strength_4h": bias_data.get('strength_4h', 0),
        "strength_1h": bias_data.get('strength_1h', 0),
        "setup_features": {
            "breakout_type": "swing" if breakout and not breakout.get('forced') else "forced",
            "breakout_index": breakout.get('break_index') if breakout else None,
            "rejection_wick_ratio": rejection.get('wick_ratio', None) if rejection else None,
            "sweep_mode": sweep.get('mode', 'unknown') if sweep else 'none',
            "sweep_forced": sweep.get('forced', False) if sweep else False
        },
        "status": "open"
    }

    # Append and save
    trades.append(trade)
    with open(TRADES_FILE, 'w') as f:
        json.dump(trades, f, indent=2)

    print(f"Trade logged: {trade['id']}")
