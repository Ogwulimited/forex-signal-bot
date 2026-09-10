"""
Strict Risk/Reward calculator – minimum 2.0.
"""

def calculate_rr(candles, direction, rejection, sweep, min_rr=2.0, debug=False):
    if not rejection or not sweep:
        return None

    if direction == 'buy':
        entry = rejection['candle']['high']
        sl = min(sweep['level'], rejection['candle']['low'])
        lookback_high = max(c['high'] for c in candles[-10:])
        tp = max(lookback_high, entry + (entry - sl) * 2)
    else:
        entry = rejection['candle']['low']
        sl = max(sweep['level'], rejection['candle']['high'])
        lookback_low = min(c['low'] for c in candles[-10:])
        tp = min(lookback_low, entry - (sl - entry) * 2)

    risk = abs(entry - sl)
    reward = abs(entry - tp)
    rr = reward / risk if risk > 0 else 0

    if rr < min_rr:
        return None

    return {'entry': entry, 'sl': sl, 'tp': tp, 'rr': rr}
