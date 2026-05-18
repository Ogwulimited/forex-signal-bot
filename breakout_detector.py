"""
Break of Structure (BOS) detector – Hybrid + Micro
1. Swing-based (wick) with window=10
2. Range breakout (close beyond 8-bar high/low)
3. Micro breakout (close beyond last 3-bar high/low)
"""

from swing_detector import find_swing_highs, find_swing_lows

def detect_breakout(candles, direction, breakout_window=10, min_bars_after_swing=3,
                    debug=False, force_breakout=False, use_wicks=True,
                    range_lookback=8, micro_lookback=3):
    if len(candles) < 20:
        if debug: print("Breakout debug: insufficient candles")
        return None

    direction_lower = direction.lower()
    swing_highs = find_swing_highs(candles, left=2, right=2)
    swing_lows = find_swing_lows(candles, left=2, right=2)

    if debug:
        print(f"Breakout debug: {len(swing_highs)} swing highs, {len(swing_lows)} swing lows")

    # 1. Swing breakout
    target_swing = None
    if direction_lower == 'buy':
        usable = [s for s in swing_highs if len(candles) - s['index'] - 1 >= min_bars_after_swing]
        if usable: target_swing = max(usable, key=lambda x: x['index'])
    else:
        usable = [s for s in swing_lows if len(candles) - s['index'] - 1 >= min_bars_after_swing]
        if usable: target_swing = max(usable, key=lambda x: x['index'])

    if target_swing:
        start_idx = max(0, len(candles) - breakout_window)
        for i in range(start_idx, len(candles)):
            candle = candles[i]
            if direction_lower == 'buy':
                if (use_wicks and candle['high'] > target_swing['level']) or candle['close'] > target_swing['level']:
                    if debug: print(f"Breakout debug: candle {i} SWING breakout (buy)")
                    return {'type': direction_lower, 'level': target_swing['level'], 'break_candle': candle, 'break_index': i, 'swing_index': target_swing['index'], 'forced': False}
            else:
                if (use_wicks and candle['low'] < target_swing['level']) or candle['close'] < target_swing['level']:
                    if debug: print(f"Breakout debug: candle {i} SWING breakout (sell)")
                    return {'type': direction_lower, 'level': target_swing['level'], 'break_candle': candle, 'break_index': i, 'swing_index': target_swing['index'], 'forced': False}

    # 2. Range breakout
    if debug: print("Breakout debug: swing failed, trying range")
    recent = candles[-range_lookback:]
    if direction_lower == 'buy':
        range_high = max(c['high'] for c in recent)
        for i in range(len(candles) - range_lookback, len(candles)):
            if candles[i]['close'] > range_high:
                if debug: print(f"Breakout debug: RANGE buy breakout c{i} close {candles[i]['close']:.5f} > {range_high:.5f}")
                return {'type': direction_lower, 'level': range_high, 'break_candle': candles[i], 'break_index': i, 'swing_index': None, 'forced': False}
    else:
        range_low = min(c['low'] for c in recent)
        for i in range(len(candles) - range_lookback, len(candles)):
            if candles[i]['close'] < range_low:
                if debug: print(f"Breakout debug: RANGE sell breakout c{i} close {candles[i]['close']:.5f} < {range_low:.5f}")
                return {'type': direction_lower, 'level': range_low, 'break_candle': candles[i], 'break_index': i, 'swing_index': None, 'forced': False}

    # 3. Micro breakout
    if debug: print("Breakout debug: range failed, trying micro (3-bar)")
    micro = candles[-micro_lookback:]
    if direction_lower == 'buy':
        micro_high = max(c['high'] for c in micro)
        if candles[-1]['close'] > micro_high:
            if debug: print(f"Breakout debug: MICRO buy breakout, close {candles[-1]['close']:.5f} > {micro_high:.5f}")
            return {'type': direction_lower, 'level': micro_high, 'break_candle': candles[-1], 'break_index': len(candles)-1, 'swing_index': None, 'forced': False}
    else:
        micro_low = min(c['low'] for c in micro)
        if candles[-1]['close'] < micro_low:
            if debug: print(f"Breakout debug: MICRO sell breakout, close {candles[-1]['close']:.5f} < {micro_low:.5f}")
            return {'type': direction_lower, 'level': micro_low, 'break_candle': candles[-1], 'break_index': len(candles)-1, 'swing_index': None, 'forced': False}

    if force_breakout and target_swing:
        force_index = max(target_swing['index'] + 1, len(candles) - 6)
        force_index = min(force_index, len(candles) - 2)
        return {'type': direction_lower, 'level': target_swing['level'], 'break_candle': candles[force_index], 'break_index': force_index, 'swing_index': target_swing['index'], 'forced': True}

    if debug: print("Breakout debug: no breakout (swing, range, micro)")
    return None
