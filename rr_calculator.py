"""
Risk/Reward calculator.
Determines entry, stop loss, take profit based on rejection and sweep.
"""

def calculate_rr(candles, direction, rejection, sweep, debug=False):
    """
    Calculate trade levels and risk/reward ratio.
    
    Parameters:
    - candles: list of candle dicts
    - direction: 'buy' or 'sell'
    - rejection: dict from rejection_detector
    - sweep: dict from liquidity_sweep_detector
    - debug: print logs
    
    Returns:
    - dict with keys: entry, sl, tp, rr, or None if invalid
    """
    if not rejection or not sweep:
        if debug:
            print("RR: missing rejection or sweep data")
        return None
    
    last_candle = candles[-1]
    
    if direction == 'buy':
        # Entry: above rejection candle high
        entry = rejection['candle']['high']
        # Stop loss: below sweep level or rejection low (whichever is lower)
        sl = min(sweep['level'], rejection['candle']['low'])
        # Take profit: use recent swing high or last high + fixed risk multiple
        # Simple: look for highest high in last 10 candles as target
        lookback_high = max(c['high'] for c in candles[-10:])
        tp = max(lookback_high, entry + (entry - sl) * 2)  # at least 2:1
        
    else:  # sell
        # Entry: below rejection candle low
        entry = rejection['candle']['low']
        # Stop loss: above sweep level or rejection high
        sl = max(sweep['level'], rejection['candle']['high'])
        # Take profit: lowest low in last 10 candles
        lookback_low = min(c['low'] for c in candles[-10:])
        tp = min(lookback_low, entry - (sl - entry) * 2)
    
    # Calculate risk and reward
    risk = abs(entry - sl)
    reward = abs(entry - tp)
    rr = reward / risk if risk > 0 else 0
    
    if debug:
        print(f"RR: entry={entry}, sl={sl}, tp={tp}, risk={risk}, reward={reward}, rr={rr:.2f}")
    
    if rr < 2.0:
        if debug:
            print(f"RR: ratio {rr:.2f} below minimum 2.0")
        return None
    
    return {
        'entry': entry,
        'sl': sl,
        'tp': tp,
        'rr': rr
        }
