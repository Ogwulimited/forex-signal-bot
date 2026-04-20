"""
Risk/Reward calculator.
Determines entry, stop loss, take profit based on rejection and sweep.
"""

def calculate_rr(candles, direction, rejection, sweep, min_rr=1.5, debug=False):
    """
    Calculate trade levels and risk/reward ratio.
    
    Parameters:
    - candles: list of candle dicts
    - direction: 'buy' or 'sell'
    - rejection: dict from rejection_detector
    - sweep: dict from liquidity_sweep_detector
    - min_rr: minimum acceptable risk/reward ratio (default 1.5)
    - debug: print logs
    
    Returns:
    - dict with keys: entry, sl, tp, rr, or None if invalid
    """
    if not rejection or not sweep:
        if debug:
            print("RR: missing rejection or sweep data")
        return None
    
    if direction == 'buy':
        entry = rejection['candle']['high']
        sl = min(sweep['level'], rejection['candle']['low'])
        lookback_high = max(c['high'] for c in candles[-10:])
        tp = max(lookback_high, entry + (entry - sl) * 2)
    else:  # sell
        entry = rejection['candle']['low']
        sl = max(sweep['level'], rejection['candle']['high'])
        lookback_low = min(c['low'] for c in candles[-10:])
        tp = min(lookback_low, entry - (sl - entry) * 2)
    
    risk = abs(entry - sl)
    reward = abs(entry - tp)
    rr = reward / risk if risk > 0 else 0
    
    if debug:
        print(f"RR: entry={entry:.5f}, sl={sl:.5f}, tp={tp:.5f}, risk={risk:.5f}, reward={reward:.5f}, rr={rr:.2f}")
    
    if rr < min_rr:
        if debug:
            print(f"RR: ratio {rr:.2f} below minimum {min_rr}")
        return None
    
    return {
        'entry': entry,
        'sl': sl,
        'tp': tp,
        'rr': rr
    }
