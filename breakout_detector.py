"""
Break of Structure (BOS) detector – Hybrid
1. Swing-based breakout (wick mode) with larger window.
2. Fallback to range breakout (close beyond recent N-bar high/low).
"""

from swing_detector import find_swing_highs, find_swing_lows

def detect_breakout(candles, direction, breakout_window=10, min_bars_after_swing=3,
                    debug=False, force_breakout=False, use_wicks=True,
                    range_lookback=8):
    """
    Detect a breakout using swing then range.

    Parameters:
    - breakout_window: number of recent candles to check for swing breakout
    - range_lookback: number of candles for fallback range breakout
    """
    if len(candles) < 20:
        if debug:
            print("Breakout debug: insufficient candles")
        return None

    direction_lower = direction.lower()
    swing_highs = find_swing_highs(candles, left=2, right=2)
    swing_lows = find_swing_lows(candles, left=2, right=2)

    if debug:
        print(f"Breakout debug: found {len(swing_highs)} swing highs, {len(swing_lows)} swing lows")

    # ---- Swing breakout ----
    target_swing = None
    if direction_lower == 'buy':
        usable = [s for s in swing_highs if len(candles) - s['index'] - 1 >= min_bars_after_swing]
        if usable:
            target_swing = max(usable, key=lambda x: x['index'])
        if debug and target_swing:
            print(f"Breakout debug: target buy swing high idx={target_swing['index']} price={target_swing['level']:.5f}")
    else:
        usable = [s for s in swing_lows if len(candles) - s['index'] - 1 >= min_bars_after_swing]
        if usable:
            target_swing = max(usable, key=lambda x: x['index'])
        if debug and target_swing:
            print(f"Breakout debug: target sell swing low idx={target_swing['index']} price={target_swing['level']:.5f}")

    if target_swing:
        start_idx = max(0, len(candles) - breakout_window)
        for i in range(start_idx, len(candles)):
            candle = candles[i]
            if direction_lower == 'buy':
                condition = candle['high'] > target_swing['level'] if use_wicks else candle['close'] > target_swing['level']
                if debug:
                    print(f"Breakout debug: candle {i}: high={candle['high']:.5f} close={candle['close']:.5f} vs {target_swing['level']:.5f}")
                if condition:
                    if debug:
                        print(f"Breakout debug: candle {i} broke swing high (wick/close)")
                    return {
                        'type': direction_lower,
                        'level': target_swing['level'],
                        'break_candle': candle,
                        'break_index': i,
                        'swing_index': target_swing['index'],
                        'forced': False
                    }
            else:
                condition = candle['low'] < target_swing['level'] if use_wicks else candle['close'] < target_swing['level']
                if debug:
                    print(f"Breakout debug: candle {i}: low={candle['low']:.5f} close={candle['close']:.5f} vs {target_swing['level']:.5f}")
                if condition:
                    if debug:
                        print(f"Breakout debug: candle {i} broke swing low (wick/close)")
                    return {
                        'type': direction_lower,
                        'level': target_swing['level'],
                        'break_candle': candle,
                        'break_index': i,
                        'swing_index': target_swing['index'],
                        'forced': False
                    }

    # ---- Fallback: Range breakout ----
    if debug:
        print("Breakout debug: swing breakout failed, trying range breakout")

    recent = candles[-range_lookback:]
    if direction_lower == 'buy':
        range_high = max(c['high'] for c in recent)
        for i in range(len(candles) - range_lookback, len(candles)):
            if candles[i]['close'] > range_high:
                if debug:
                    print(f"Breakout debug: range breakout BUY at candle {i}, close {candles[i]['close']:.5f} > range high {range_high:.5f}")
                return {
                    'type': direction_lower,
                    'level': range_high,
                    'break_candle': candles[i],
                    'break_index': i,
                    'swing_index': None,
                    'forced': False
                }
    else:
        range_low = min(c['low'] for c in recent)
        for i in range(len(candles) - range_lookback, len(candles)):
            if candles[i]['close'] < range_low:
                if debug:
                    print(f"Breakout debug: range breakout SELL at candle {i}, close {candles[i]['close']:.5f} < range low {range_low:.5f}")
                return {
                    'type': direction_lower,
                    'level': range_low,
                    'break_candle': candles[i],
                    'break_index': i,
                    'swing_index': None,
                    'forced': False
                }

    if force_breakout and target_swing:
        force_index = max(target_swing['index'] + 1, len(candles) - 6)
        force_index = min(force_index, len(candles) - 2)
        return {
            'type': direction_lower,
            'level': target_swing['level'],
            'break_candle': candles[force_index],
            'break_index': force_index,
            'swing_index': target_swing['index'],
            'forced': True
        }

    if debug:
        print("Breakout debug: no breakout (swing or range)")
    return None
