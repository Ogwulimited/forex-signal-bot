"""
Retest Detector – Relaxed
Detects when price returns to a broken level.
If breakout is too fresh (last 2 candles), assumes a synthetic retest.
"""

def detect_retest(candles, breakout, direction, tolerance_ratio=0.0003, max_retest_bars=10, debug=False):
    """
    Find a retest of the breakout level.
    
    Returns:
    - dict with 'index', 'candle', or None
    """
    if breakout is None:
        if debug:
            print("Retest: no breakout provided")
        return None

    breakout_index = breakout.get('break_index')
    if breakout_index is None:
        if debug:
            print("Retest: breakout missing 'break_index'")
        return None

    level = breakout.get('level')
    if level is None:
        if debug:
            print("Retest: breakout missing 'level'")
        return None

    tolerance = tolerance_ratio * level
    end_idx = len(candles) - 1

    if debug:
        print(f"Retest: looking for retest of level {level:.5f} after index {breakout_index} (tolerance {tolerance:.5f})")

    # Search for real retest
    start = breakout_index + 1
    if start <= end_idx:
        for i in range(start, min(start + max_retest_bars, end_idx + 1)):
            candle = candles[i]
            if direction == 'buy':
                # Buy retest: candle low touches breakout level, close above
                if candle['low'] <= level + tolerance and candle['close'] > level:
                    if debug:
                        print(f"Retest: found buy retest at index {i}, low={candle['low']:.5f} close={candle['close']:.5f}")
                    return {'index': i, 'candle': candle}
            else:  # sell
                if candle['high'] >= level - tolerance and candle['close'] < level:
                    if debug:
                        print(f"Retest: found sell retest at index {i}, high={candle['high']:.5f} close={candle['close']:.5f}")
                    return {'index': i, 'candle': candle}

    # No real retest – if breakout is very fresh, allow synthetic
    if breakout_index >= len(candles) - 2:
        if debug:
            print(f"Retest: no real retest, but breakout too fresh (idx {breakout_index}) – using synthetic retest")
        return {
            'index': breakout_index,
            'candle': candles[breakout_index],
            'synthetic': True
        }

    if debug:
        print(f"Retest: no retest found within {max_retest_bars} candles after breakout")
    return None
