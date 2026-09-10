"""
Strict Retest Detector – only real retests, no synthetic.
"""

def detect_retest(candles, breakout, direction, tolerance_ratio=0.0003, max_retest_bars=10, debug=False):
    if breakout is None:
        return None

    breakout_index = breakout.get('break_index')
    level = breakout.get('level')
    if breakout_index is None or level is None:
        return None

    tolerance = tolerance_ratio * level
    end_idx = len(candles) - 1
    start = breakout_index + 1
    if start > end_idx:
        return None

    for i in range(start, min(start + max_retest_bars, end_idx + 1)):
        candle = candles[i]
        if direction == 'buy':
            if candle['low'] <= level + tolerance and candle['close'] > level:
                return {'index': i, 'candle': candle}
        else:
            if candle['high'] >= level - tolerance and candle['close'] < level:
                return {'index': i, 'candle': candle}
    return None
