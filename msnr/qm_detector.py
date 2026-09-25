"""
MSNR QM (Break of Structure) Detector

A QM is a structural break: recent swings were making directional
structure in one direction, and then price closes beyond the most
recent opposing swing, breaking that structure.

  Bullish QM: recent swing highs descending + recent swing lows
              descending (bearish structure) → price closes above
              the most recent swing high.
  Bearish QM: recent swing highs ascending + recent swing lows
              ascending (bullish structure) → price closes below
              the most recent swing low.

MSNR treats "QM" and "breakout" as the same thing.
Close-based only. Wicks do not count.
"""

from swing_detector import find_swing_highs, find_swing_lows


def _is_descending(values, tolerance=0.0):
    """True if each element is strictly less than the previous (with tolerance)."""
    for i in range(1, len(values)):
        if values[i] >= values[i - 1] - tolerance:
            return False
    return True


def _is_ascending(values, tolerance=0.0):
    """True if each element is strictly greater than the previous (with tolerance)."""
    for i in range(1, len(values)):
        if values[i] <= values[i - 1] + tolerance:
            return False
    return True


def detect_qm(candles, direction, lookback=150, min_swings=4,
              tolerance_pips=0.0, pair=None, debug=False):
    """
    Detect a QM in the given direction.

    Parameters:
    - candles: list of candle dicts (need 'open', 'high', 'low', 'close')
    - direction: 'bullish' or 'bearish' — which way the QM breaks
    - lookback: how many recent candles to consider for swings
    - min_swings: minimum number of swings needed to confirm structure
    - tolerance_pips: allowed noise in swing comparison (e.g., equal highs)
    - pair: used to convert tolerance_pips to price
    - debug: print reasoning

    Returns:
    - dict or None:
      {
        'direction': 'bullish' | 'bearish',
        'break_index': int,       # candle index that broke structure
        'break_level': float,     # the swing level that was broken
        'break_candle': dict,     # the breaking candle
        'structure_highs': list,  # swing highs of the pre-break structure
        'structure_lows': list,   # swing lows of the pre-break structure
        'candles_since_break': int,
      }
    """
    if len(candles) < 20:
        return None

    window_start = max(0, len(candles) - lookback)
    window = candles[window_start:]

    # Convert tolerance from pips to price if provided
    if tolerance_pips and pair:
        from zone_filter import PIP_SCALE
        tol = tolerance_pips * PIP_SCALE.get(pair, 0.0001)
    else:
        tol = 0.0

    # Find swings in the window (left/right = 2 like the instructor)
    swing_highs = find_swing_highs(window, left=2, right=2)
    swing_lows = find_swing_lows(window, left=2, right=2)

    if debug:
        print(f"  [QM-{direction}] swings in last {len(window)} candles: "
              f"{len(swing_highs)} highs, {len(swing_lows)} lows")

    if len(swing_highs) < min_swings // 2 or len(swing_lows) < min_swings // 2:
        if debug:
            print(f"  [QM-{direction}] insufficient swings")
        return None

    # Take the last few swings to evaluate structure
    recent_highs = swing_highs[-4:]
    recent_lows = swing_lows[-4:]

    high_levels = [s['level'] for s in recent_highs]
    low_levels = [s['level'] for s in recent_lows]

    if debug:
        print(f"  [QM-{direction}] recent highs: {[round(x,5) for x in high_levels]}")
        print(f"  [QM-{direction}] recent lows:  {[round(x,5) for x in low_levels]}")

    # Determine structure before the break
    if direction == 'bullish':
        # Need: descending highs AND descending lows (bearish structure)
        structure_ok = _is_descending(high_levels, tol) and _is_descending(low_levels, tol)
        if not structure_ok:
            if debug:
                print(f"  [QM-bullish] structure not descending — no bullish QM")
            return None

        # Break level = the most recent swing high before the break
        last_high = recent_highs[-1]
        break_level = last_high['level']
        break_swing_window_idx = last_high['index']

        # Search for a candle AFTER the break-swing that closes above break_level
        # Convert window index to full-candle index for downstream use
        break_swing_full_idx = window_start + break_swing_window_idx

        for i in range(break_swing_full_idx + 1, len(candles)):
            c = candles[i]
            if c['close'] > break_level:
                if debug:
                    print(f"  [QM-bullish] ✅ break at candle {i} "
                          f"(close {c['close']:.5f} > {break_level:.5f})")
                return {
                    'direction': 'bullish',
                    'break_index': i,
                    'break_level': break_level,
                    'break_candle': c,
                    'structure_highs': high_levels,
                    'structure_lows': low_levels,
                    'candles_since_break': len(candles) - 1 - i,
                }

    else:  # bearish
        # Need: ascending highs AND ascending lows (bullish structure)
        structure_ok = _is_ascending(high_levels, tol) and _is_ascending(low_levels, tol)
        if not structure_ok:
            if debug:
                print(f"  [QM-bearish] structure not ascending — no bearish QM")
            return None

        last_low = recent_lows[-1]
        break_level = last_low['level']
        break_swing_window_idx = last_low['index']
        break_swing_full_idx = window_start + break_swing_window_idx

        for i in range(break_swing_full_idx + 1, len(candles)):
            c = candles[i]
            if c['close'] < break_level:
                if debug:
                    print(f"  [QM-bearish] ✅ break at candle {i} "
                          f"(close {c['close']:.5f} < {break_level:.5f})")
                return {
                    'direction': 'bearish',
                    'break_index': i,
                    'break_level': break_level,
                    'break_candle': c,
                    'structure_highs': high_levels,
                    'structure_lows': low_levels,
                    'candles_since_break': len(candles) - 1 - i,
                }

    if debug:
        print(f"  [QM-{direction}] structure present but no break candle found")
    return None
