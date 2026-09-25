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

v3 changes:
  - Sliding 3-swing window over last 5 swings (allows detection
    even after new candles form subsequent swings post-break)
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


def detect_qm(candles, direction, lookback=150, min_swings=6,
              tolerance_pips=0.0, pair=None, debug=False):
    """
    Detect a QM in the given direction, using a sliding 3-swing window
    over the last 5 swings. This allows detection of a QM even after
    new candles have formed subsequent swings post-break.

    Parameters:
    - candles: list of candle dicts (need 'open', 'high', 'low', 'close')
    - direction: 'bullish' or 'bearish' — which way the QM breaks
    - lookback: how many recent candles to consider for swings
    - min_swings: kept for API compatibility (unused)
    - tolerance_pips: allowed noise in swing comparison
    - pair: used to convert tolerance_pips to price
    - debug: print reasoning

    Returns:
    - dict or None
    """
    if len(candles) < 20:
        return None

    window_start = max(0, len(candles) - lookback)
    window = candles[window_start:]

    if tolerance_pips and pair:
        from zone_filter import PIP_SCALE
        tol = tolerance_pips * PIP_SCALE.get(pair, 0.0001)
    else:
        tol = 0.0

    swing_highs = find_swing_highs(window, left=2, right=2)
    swing_lows = find_swing_lows(window, left=2, right=2)

    if debug:
        print(f"  [QM-{direction}] swings in last {len(window)} candles: "
              f"{len(swing_highs)} highs, {len(swing_lows)} lows")

    if len(swing_highs) < 3 or len(swing_lows) < 3:
        if debug:
            print(f"  [QM-{direction}] insufficient swings")
        return None

    # Take the last 5 swings on each side
    recent_highs = swing_highs[-5:]
    recent_lows = swing_lows[-5:]

    high_levels = [s['level'] for s in recent_highs]
    low_levels = [s['level'] for s in recent_lows]

    if debug:
        print(f"  [QM-{direction}] recent highs: {[round(x,5) for x in high_levels]}")
        print(f"  [QM-{direction}] recent lows:  {[round(x,5) for x in low_levels]}")

    n_highs = len(recent_highs)
    n_lows = len(recent_lows)

    # Try 3-swing windows from most recent backward
    for offset in range(0, max(1, n_highs - 2)):
        if direction == 'bearish':
            if n_lows - 2 - offset < 0 or n_highs - 2 - offset < 0:
                continue
            h_start = n_highs - 3 - offset
            l_start = n_lows - 3 - offset
            if h_start < 0 or l_start < 0:
                continue
            h_window = high_levels[h_start:h_start + 3]
            l_window = low_levels[l_start:l_start + 3]
            if not (_is_ascending(h_window, tol) and _is_ascending(l_window, tol)):
                continue

            break_swing = recent_lows[l_start + 2]
            break_level = break_swing['level']
            break_swing_full = window_start + break_swing['index']

            for i in range(break_swing_full + 1, len(candles)):
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
                        'structure_highs': h_window,
                        'structure_lows': l_window,
                        'candles_since_break': len(candles) - 1 - i,
                    }

        else:  # bullish
            if n_lows - 2 - offset < 0 or n_highs - 2 - offset < 0:
                continue
            h_start = n_highs - 3 - offset
            l_start = n_lows - 3 - offset
            if h_start < 0 or l_start < 0:
                continue
            h_window = high_levels[h_start:h_start + 3]
            l_window = low_levels[l_start:l_start + 3]
            if not (_is_descending(h_window, tol) and _is_descending(l_window, tol)):
                continue

            break_swing = recent_highs[h_start + 2]
            break_level = break_swing['level']
            break_swing_full = window_start + break_swing['index']

            for i in range(break_swing_full + 1, len(candles)):
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
                        'structure_highs': h_window,
                        'structure_lows': l_window,
                        'candles_since_break': len(candles) - 1 - i,
                    }

    if debug:
        print(f"  [QM-{direction}] no qualifying window found")
    return None
