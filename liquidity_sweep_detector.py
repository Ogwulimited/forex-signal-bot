"""
Improved liquidity sweep detector using swing points.
Detects when price sweeps a recent swing low (for buy) or swing high (for sell)
before a breakout/retest.
"""

from swing_detector import find_swing_highs, find_swing_lows

def detect_liquidity_sweep(candles, direction, breakout=None, retest=None, lookback=20, debug=False, force_sweep=False):
    """
    Detect if a liquidity sweep occurred before the potential entry.
    
    Parameters:
    - candles: list of candle dicts with 'high', 'low', 'close'
    - direction: 'buy' or 'sell'
    - breakout: breakout dict (optional, for sequence alignment)
    - retest: retest dict (optional)
    - lookback: number of candles to look back for swing points
    - debug: print logs
    - force_sweep: if True and no real sweep, return simulated sweep
    
    Returns:
    - dict with keys: level, sweep_index, type, forced (bool), candle
    - None if no sweep and force_sweep=False
    """
    
    if len(candles) < lookback:
        if debug:
            print("Liquidity sweep: insufficient candles")
        return None
    
    # Determine the reference point for "before" – either retest index or breakout index
    reference_index = len(candles) - 1  # default to last candle
    if retest and retest.get('retest_index') is not None:
        reference_index = retest['retest_index']
    elif breakout and breakout.get('break_index') is not None:
        reference_index = breakout['break_index']
    
    if debug:
        print(f"Liquidity sweep: looking for sweep before index {reference_index}")
    
    # Find swings up to reference_index (excluding candles after reference)
    relevant_candles = candles[:reference_index + 1]
    swing_highs = find_swing_highs(relevant_candles, left=2, right=2)
    swing_lows = find_swing_lows(relevant_candles, left=2, right=2)
    
    # We only consider swings that are at least 'lookback' candles before reference
    min_swing_index = max(0, reference_index - lookback)
    
    if direction == 'buy':
        # Need a recent swing low that was swept (price went below then closed above)
        # Filter swing lows within lookback period
        recent_swing_lows = [s for s in swing_lows if min_swing_index <= s['index'] < reference_index]
        if not recent_swing_lows:
            if debug:
                print("Liquidity sweep: no recent swing lows found")
        else:
            # Take the most recent swing low (largest index)
            target_swing = max(recent_swing_lows, key=lambda x: x['index'])
            sweep_level = target_swing['level']
            if debug:
                print(f"Liquidity sweep: checking swing low at index {target_swing['index']} level={sweep_level}")
            
            # Check candles after the swing low but before reference for a sweep
            for i in range(target_swing['index'] + 1, reference_index):
                candle = candles[i]
                if candle['low'] < sweep_level and candle['close'] > sweep_level:
                    if debug:
                        print(f"Liquidity sweep: buy sweep detected at index {i}, low={candle['low']}, close={candle['close']}")
                    return {
                        'level': sweep_level,
                        'sweep_index': i,
                        'type': 'buy_sweep',
                        'candle': candle,
                        'forced': False
                    }
            if debug:
                print("Liquidity sweep: no sweep of the recent swing low")
    
    else:  # sell
        recent_swing_highs = [s for s in swing_highs if min_swing_index <= s['index'] < reference_index]
        if not recent_swing_highs:
            if debug:
                print("Liquidity sweep: no recent swing highs found")
        else:
            target_swing = max(recent_swing_highs, key=lambda x: x['index'])
            sweep_level = target_swing['level']
            if debug:
                print(f"Liquidity sweep: checking swing high at index {target_swing['index']} level={sweep_level}")
            
            for i in range(target_swing['index'] + 1, reference_index):
                candle = candles[i]
                if candle['high'] > sweep_level and candle['close'] < sweep_level:
                    if debug:
                        print(f"Liquidity sweep: sell sweep detected at index {i}, high={candle['high']}, close={candle['close']}")
                    return {
                        'level': sweep_level,
                        'sweep_index': i,
                        'type': 'sell_sweep',
                        'candle': candle,
                        'forced': False
                    }
            if debug:
                print("Liquidity sweep: no sweep of the recent swing high")
    
    # No real sweep – force if requested
    if force_sweep:
        if debug:
            print(f"Liquidity sweep: FORCING simulated sweep for {direction}")
        # Create a fake sweep using the last candle before reference_index
        fake_index = max(0, reference_index - 1)
        fake_candle = candles[fake_index]
        if direction == 'buy':
            fake_level = fake_candle['low'] * 0.999
            return {
                'level': fake_level,
                'sweep_index': fake_index,
                'type': 'buy_sweep',
                'candle': fake_candle,
                'forced': True
            }
        else:
            fake_level = fake_candle['high'] * 1.001
            return {
                'level': fake_level,
                'sweep_index': fake_index,
                'type': 'sell_sweep',
                'candle': fake_candle,
                'forced': True
            }
    
    return None
