"""
Confidence Engine – Analyses historical trades to score new signals.
"""
import json
import os
from datetime import datetime

TRADES_FILE = "trades.json"
MIN_SAMPLE_SIZE = 5

def load_completed_trades():
    """Return list of trades with status 'win' or 'loss'."""
    if not os.path.exists(TRADES_FILE):
        return []
    with open(TRADES_FILE, 'r') as f:
        try:
            all_trades = json.load(f)
        except json.JSONDecodeError:
            return []
    return [t for t in all_trades if t.get('status') in ('win', 'loss')]

def classify_wick_ratio(ratio):
    if ratio is None:
        return "unknown"
    if ratio < 0.5:
        return "low"
    elif ratio < 1.0:
        return "medium"
    else:
        return "high"

def classify_rr(rr):
    if rr is None:
        return "unknown"
    if rr < 1.5:
        return "low"
    elif rr <= 2.5:
        return "medium"
    else:
        return "high"

def get_session():
    hour = datetime.utcnow().hour
    if 7 <= hour < 16:
        return "London"
    elif 12 <= hour < 20:
        return "New York"
    elif 0 <= hour < 7:
        return "Asian"
    else:
        return "Other"

def get_similar_trades(signal, bias_data, breakout, rejection, sweep):
    """Filter completed trades that resemble the current setup."""
    completed = load_completed_trades()
    if not completed:
        return [], 0

    direction = signal['direction']
    pair = signal['pair']
    session = get_session()
    bias_4h = bias_data.get('bias_4h', 'unknown')
    breakout_type = "swing" if breakout and not breakout.get('forced') else "forced"
    sweep_mode = sweep.get('mode', 'adaptive') if sweep else 'unknown'
    rejection_wick = rejection.get('wick_ratio', None) if rejection else None
    wick_class = classify_wick_ratio(rejection_wick)
    rr_class = classify_rr(signal.get('rr', 0))

    similar = []
    for t in completed:
        if t.get('pair') != pair:
            continue
        if t.get('direction') != direction:
            continue
        if t.get('session') != session:
            continue
        if t.get('bias_4h') != bias_4h:
            continue
        bt = t.get('setup_features', {}).get('breakout_type', 'unknown')
        if bt != breakout_type:
            continue
        sm = t.get('setup_features', {}).get('sweep_mode', 'unknown')
        if sm != sweep_mode:
            continue
        hist_wick = t.get('setup_features', {}).get('rejection_wick_ratio')
        hist_wick_class = classify_wick_ratio(hist_wick)
        if hist_wick_class != wick_class:
            continue
        hist_rr = t.get('rr')
        hist_rr_class = classify_rr(hist_rr)
        if hist_rr_class != rr_class:
            continue
        similar.append(t)

    return similar, len(completed)

def calculate_confidence(similar_trades):
    total = len(similar_trades)
    if total < MIN_SAMPLE_SIZE:
        return None
    wins = sum(1 for t in similar_trades if t.get('status') == 'win')
    win_rate = (wins / total) * 100
    avg_rr = sum(t.get('r_multiple', 0) for t in similar_trades) / total
    return {
        'win_rate': round(win_rate, 1),
        'sample_size': total,
        'avg_rr': round(avg_rr, 2),
        'wins': wins,
        'losses': total - wins
    }

def get_signal_confidence(signal, bias_data, breakout, rejection, sweep):
    """Return confidence dict or None if insufficient history."""
    similar, _ = get_similar_trades(signal, bias_data, breakout, rejection, sweep)
    return calculate_confidence(similar)
