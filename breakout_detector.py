"""
Strict Swing Break of Structure (BOS) detector.
Breakout only when price CLOSES beyond a prior swing high/low.
No range or micro fallbacks.
"""

from swing_detector import find_swing_highs, find_swing_lows

def detect_breakout(candles, direction, breakout_window=5, min_bars_after_swing=3,
                    debug=False, force_breakout=False):
    if len(candles) < 20:
        return None

    direction_lower = direction.lower()
    swing_highs = find_swing_highs(candles, left=2, right=2)
    swing_lows = find_swing_lows(candles, left=2, right=2)

    target_swing = None
    if direction_lower == 'buy':
        usable = [s for s in swing_highs if len(candles) - s['index'] - 1 >= min_bars_after_swing]
        if usable:
            target_swing = max(usable, key=lambda x: x['index'])
    else:
        usable = [s for s in swing_lows if len(candles) - s['index'] - 1 >= min_bars_after_swing]
        if usable:
            target_swing = max(usable, key=lambda x: x['index'])

    if target_swing is None:
        return None

    start_idx = max(0, len(candles) - breakout_window)
    for i in range(start_idx, len(candles)):
        candle = candles[i]
        if direction_lower == 'buy':
            if candle['close'] > target_swing['level']:
                if debug: print(f"Breakout: candle {i} close {candle['close']} broke swing high {target_swing['level']}")
                return {
                    'type': 'buy',
                    'level': target_swing['level'],
                    'break_candle': candle,
                    'break_index': i,
                    'swing_index': target_swing['index'],
                    'forced': False
                }
        else:
            if candle['close'] < target_swing['level']:
                if debug: print(f"Breakout: candle {i} close {candle['close']} broke swing low {target_swing['level']}")
                return {
                    'type': 'sell',
                    'level': target_swing['level'],
                    'break_candle': candle,
                    'break_index': i,
                    'swing_index': target_swing['index'],
                    'forced': False
                }
    return None
