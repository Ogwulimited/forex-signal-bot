"""
Swing-based Break of Structure (BOS) detector – Relaxed
Accepts wick breaks (high/low beyond swing) in addition to closes.
"""

from swing_detector import find_swing_highs, find_swing_lows

def detect_breakout(candles, direction, breakout_window=5, min_bars_after_swing=3,
                    debug=False, force_breakout=False, use_wicks=True):
    """
    Detect if price has broken a prior swing level.
    
    Parameters:
    - candles: list of dicts with 'high','low','close'
    - direction: 'buy' or 'sell'
    - breakout_window: number of recent candles to check
    - min_bars_after_swing: min candles after swing before valid
    - debug: print detailed logs
    - force_breakout: simulate breakout if none real
    - use_wicks: if True, break of high/low counts; if False, only close breaks
    
    Returns:
    - dict with keys: type, level, break_candle, break_index, swing_index, forced
    """
    if len(candles) < 20:
        if debug:
            print("Breakout debug: insufficient candles")
        return None

    swing_highs = find_swing_highs(candles, left=2, right=2)
    swing_lows = find_swing_lows(candles, left=2, right=2)

    if debug:
        print(f"Breakout debug: found {len(swing_highs)} swing highs and {len(swing_lows)} swing lows.")

    target_swing = None
    direction_lower = direction.lower()

    if direction_lower == 'buy':
        usable_swings = [s for s in swing_highs if len(candles) - s['index'] - 1 >= min_bars_after_swing]
        if usable_swings:
            target_swing = max(usable_swings, key=lambda x: x['index'])
        if debug and target_swing:
            print(f"Breakout debug: target buy swing high at index={target_swing['index']} price={target_swing['level']}")
    else:
        usable_swings = [s for s in swing_lows if len(candles) - s['index'] - 1 >= min_bars_after_swing]
        if usable_swings:
            target_swing = max(usable_swings, key=lambda x: x['index'])
        if debug and target_swing:
            print(f"Breakout debug: target sell swing low at index={target_swing['index']} price={target_swing['level']}")

    if target_swing is None:
        if debug:
            print("Breakout debug: no usable swing found")
        if force_breakout:
            if direction_lower == 'buy' and swing_highs:
                target_swing = max(swing_highs, key=lambda x: x['index'])
            elif direction_lower == 'sell' and swing_lows:
                target_swing = max(swing_lows, key=lambda x: x['index'])
        if target_swing is None:
            return None

    start_idx = max(0, len(candles) - breakout_window)
    breakout_found = False
    break_candle = None
    break_index = None

    for i in range(start_idx, len(candles)):
        candle = candles[i]
        if direction_lower == 'buy':
            # Check breakout condition
            if use_wicks:
                breakout_condition = candle['high'] > target_swing['level']
            else:
                breakout_condition = candle['close'] > target_swing['level']
            if debug:
                print(f"Breakout debug: candle {i}: high={candle['high']:.5f}, close={candle['close']:.5f} vs swing high {target_swing['level']:.5f}")
            if breakout_condition:
                breakout_found = True
                break_candle = candle
                break_index = i
                if debug:
                    print(f"Breakout debug: candle {i} broke above swing high ({'wick' if candle['high'] > target_swing['level'] and candle['close'] <= target_swing['level'] else 'close'})")
                break
        else:  # sell
            if use_wicks:
                breakout_condition = candle['low'] < target_swing['level']
            else:
                breakout_condition = candle['close'] < target_swing['level']
            if debug:
                print(f"Breakout debug: candle {i}: low={candle['low']:.5f}, close={candle['close']:.5f} vs swing low {target_swing['level']:.5f}")
            if breakout_condition:
                breakout_found = True
                break_candle = candle
                break_index = i
                if debug:
                    print(f"Breakout debug: candle {i} broke below swing low ({'wick' if candle['low'] < target_swing['level'] and candle['close'] >= target_swing['level'] else 'close'})")
                break

    if breakout_found:
        return {
            'type': direction_lower,
            'level': target_swing['level'],
            'break_candle': break_candle,
            'break_index': break_index,
            'swing_index': target_swing['index'],
            'forced': False
        }

    if force_breakout:
        if debug:
            print(f"Breakout debug: FORCING simulated breakout.")
        force_index = max(target_swing['index'] + 1, len(candles) - 6)
        force_index = min(force_index, len(candles) - 2)
        break_candle = candles[force_index]
        return {
            'type': direction_lower,
            'level': target_swing['level'],
            'break_candle': break_candle,
            'break_index': force_index,
            'swing_index': target_swing['index'],
            'forced': True
        }

    if debug:
        print("Breakout debug: no candle broke target swing level.")
    return None
