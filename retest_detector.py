"""
Retest detector.
Checks if price returns to the breakout level after a break of structure.
"""

def detect_retest(candles, breakout, direction, tolerance_ratio=0.0003, max_retest_bars=10, debug=False):
    """
    Detect retest of breakout level.
    
    Parameters:
    - candles: list of candle dicts
    - breakout: dict from breakout_detector (contains 'level')
    - direction: 'buy' or 'sell'
    - tolerance_ratio: allowed distance from level as fraction of price
    - max_retest_bars: how many candles after breakout to check
    - debug: print logs
    
    Returns:
    - dict with keys: level, retest_index, candle, or None
    """
    if not breakout:
        return None
    
    breakout_level = breakout['level']
    break_index = breakout['break_index']
    tolerance = breakout_level * tolerance_ratio
    
    if debug:
        print(f"Retest: looking for retest of level {breakout_level} after index {break_index}")
    
    # Start checking from the candle after the break candle
    start = break_index + 1
    end = min(len(candles), start + max_retest_bars)
    
    for i in range(start, end):
        candle = candles[i]
        if direction == 'buy':
            # Retest means price drops back to or below breakout level, then closes above
            if candle['low'] <= breakout_level + tolerance:
                # Also need close above level (or at least not far below)
                if candle['close'] > breakout_level - tolerance:
                    if debug:
                        print(f"Retest: found buy retest at index {i}, low={candle['low']}, close={candle['close']}")
                    return {
                        'level': breakout_level,
                        'retest_index': i,
                        'candle': candle,
                        'type': 'buy_retest'
                    }
        else:  # sell
            # Retest means price rises back to or above breakout level, then closes below
            if candle['high'] >= breakout_level - tolerance:
                if candle['close'] < breakout_level + tolerance:
                    if debug:
                        print(f"Retest: found sell retest at index {i}, high={candle['high']}, close={candle['close']}")
                    return {
                        'level': breakout_level,
                        'retest_index': i,
                        'candle': candle,
                        'type': 'sell_retest'
                    }
    
    if debug:
        print(f"Retest: no retest found within {max_retest_bars} candles after breakout")
    return None
