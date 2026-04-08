"""
Swing-based Break of Structure (BOS) detector.
Identifies when price breaks beyond a prior swing high (buy) or swing low (sell).
"""

from swing_detector import find_swing_highs, find_swing_lows

def detect_breakout(candles, direction, breakout_window=5, min_bars_after_swing=3, debug=False, force_breakout=False):
    """
    Detect if price has broken a prior swing level.
    
    Parameters:
    - candles: list of candle dicts with 'high', 'low', 'close'
    - direction: 'buy' or 'sell'
    - breakout_window: number of recent candles to check for breakout
    - min_bars_after_swing: minimum candles after a swing before considering it valid
    - debug: print detailed logs
    - force_breakout: if True and no real breakout, return simulated breakout using target swing
    
    Returns:
    - dict with keys: type, level, break_candle, break_index, swing_index, forced (if simulated)
    - None if no breakout and force_breakout=False
    """
    
    if len(candles) < 20:
        if debug:
            print("Breakout debug: insufficient candles")
        return None
    
    # Find all swing highs and lows
    swing_highs = find_swing_highs(candles, left=2, right=2)
    swing_lows = find_swing_lows(candles, left=2, right=2)
    
    if debug:
        print(f"Breakout debug: found {len(swing_highs)} swing highs and {len(swing_lows)} swing lows.")
    
    target_swing = None
    direction_lower = direction.lower()
    
    if direction_lower == 'buy':
        # Need to break above a swing high
        # Filter swings that have at least min_bars_after_swing candles after them
        usable_swings = [s for s in swing_highs if len(candles) - s['index'] - 1 >= min_bars_after_swing]
        if usable_swings:
            # Take the most recent (largest index)
            target_swing = max(usable_swings, key=lambda x: x['index'])
        if debug and target_swing:
            print(f"Breakout debug: target buy swing high at index={target_swing['index']} price={target_swing['level']}")
            
    elif direction_lower == 'sell':
        # Need to break below a swing low
        usable_swings = [s for s in swing_lows if len(candles) - s['index'] - 1 >= min_bars_after_swing]
        if usable_swings:
            target_swing = max(usable_swings, key=lambda x: x['index'])
        if debug and target_swing:
            print(f"Breakout debug: target sell swing low at index={target_swing['index']} price={target_swing['level']}")
    else:
        if debug:
            print("Breakout debug: invalid direction")
        return None
    
    if target_swing is None:
        if debug:
            print("Breakout debug: no usable swing found (insufficient bars after swing)")
        # If force_breakout, try to use the most recent swing regardless of bars after
        if force_breakout:
            if direction_lower == 'buy' and swing_highs:
                target_swing = max(swing_highs, key=lambda x: x['index'])
                if debug:
                    print(f"Breakout debug: FORCING - using most recent swing high at index={target_swing['index']} price={target_swing['level']}")
            elif direction_lower == 'sell' and swing_lows:
                target_swing = max(swing_lows, key=lambda x: x['index'])
                if debug:
                    print(f"Breakout debug: FORCING - using most recent swing low at index={target_swing['index']} price={target_swing['level']}")
        if target_swing is None:
            return None
    
    # Check recent candles for breakout
    start_idx = max(0, len(candles) - breakout_window)
    breakout_found = False
    break_candle = None
    break_index = None
    
    for i in range(start_idx, len(candles)):
        candle = candles[i]
        if direction_lower == 'buy':
            if candle['close'] > target_swing['level']:
                breakout_found = True
                break_candle = candle
                break_index = i
                if debug:
                    print(f"Breakout debug: candle index={i} close={candle['close']} broke above swing high {target_swing['level']}")
                break
            elif debug:
                print(f"Breakout debug: checking candle index={i} close={candle['close']} against swing high={target_swing['level']}")
        else:  # sell
            if candle['close'] < target_swing['level']:
                breakout_found = True
                break_candle = candle
                break_index = i
                if debug:
                    print(f"Breakout debug: candle index={i} close={candle['close']} broke below swing low {target_swing['level']}")
                break
            elif debug:
                print(f"Breakout debug: checking candle index={i} close={candle['close']} against swing low={target_swing['level']}")
    
    if breakout_found:
        return {
            'type': direction_lower,
            'level': target_swing['level'],
            'break_candle': break_candle,
            'break_index': break_index,
            'swing_index': target_swing['index'],
            'forced': False
        }
    
    # No real breakout - force one if requested
    if force_breakout:
        if debug:
            print(f"Breakout debug: FORCING simulated breakout for debugging. Using target {direction_lower} level={target_swing['level']}")
        # Use the last candle as the simulated break candle
        last_candle = candles[-1]
        return {
            'type': direction_lower,
            'level': target_swing['level'],
            'break_candle': last_candle,
            'break_index': len(candles) - 1,
            'swing_index': target_swing['index'],
            'forced': True
        }
    
    if debug:
        print("Breakout debug: no candle closed beyond target swing level.")
    return None
