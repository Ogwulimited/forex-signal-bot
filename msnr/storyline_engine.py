"""
MSNR Storyline Engine

Detects the active Daily storyline via the two-factor test:

  Factor 1: Daily rejection on the Daily timeframe
    - Bearish storyline: Daily closed below a Daily resistance
    - Bullish storyline: Daily closed above a Daily support

  Factor 2: H4 breakout (QM) in the matching direction

Both factors must be present and aligned. Neither alone establishes a storyline.
"""

from zone_detector import detect_all_zones
from zone_filter import filter_zones
from qm_detector import detect_qm


# How many recent Daily candles to inspect for rejections
REJECTION_LOOKBACK_DAYS = 3

# Maximum age (in H4 candles) for an H4 QM to count as "fresh"
# 12 H4 candles = 48 hours
MAX_QM_AGE_H4 = 12


def _check_daily_rejection(daily_candles, daily_zones, debug=False):
    """
    Scan recent Daily candles for zone rejections.
    Returns list of rejection dicts.
    """
    rejections = []
    n = len(daily_candles)
    start = max(0, n - REJECTION_LOOKBACK_DAYS)

    for i in range(start, n):
        candle = daily_candles[i]
        for zone in daily_zones:
            if zone['type'] in ('resistance', 'flip'):
                # Resistance rejection: candle wicked into/above zone,
                # closed below the zone level
                if candle['high'] >= zone['level'] and candle['close'] < zone['level']:
                    rejections.append({
                        'direction': 'bearish',
                        'zone': zone,
                        'candle_index': i,
                        'candle': candle,
                    })
            if zone['type'] in ('support', 'flip'):
                # Support rejection: candle wicked into/below zone,
                # closed above the zone level
                if candle['low'] <= zone['level'] and candle['close'] > zone['level']:
                    rejections.append({
                        'direction': 'bullish',
                        'zone': zone,
                        'candle_index': i,
                        'candle': candle,
                    })

    if debug:
        print(f"  [STORY] Daily rejections found: {len(rejections)}")
        for r in rejections:
            print(f"    {r['direction']:>8} via {r['zone']['type']} "
                  f"@ {r['zone']['level']:.5f} (day idx {r['candle_index']})")

    return rejections


def detect_daily_storyline(pair, daily_candles, h4_candles, debug=False):
    """
    Detect the currently active Daily storyline.

    Returns:
    - dict or None:
      {
        'storyline': 'bullish' | 'bearish',
        'rejection_zone': {...},
        'rejection_candle': {...},
        'h4_qm': {...},
        'h4_zone': {...},   # derived: the H4 zone aligned with the storyline
      }
    """
    if len(daily_candles) < 30 or len(h4_candles) < 30:
        return None

    # ─── Factor 1: Daily rejection ───
    daily_zones_raw = detect_all_zones(daily_candles, min_open_close_run=2, debug=False)
    daily_zones = filter_zones(daily_zones_raw, daily_candles, pair, debug=False)

    if debug:
        print(f"  [STORY] Daily zones (filtered): {len(daily_zones)}")

    rejections = _check_daily_rejection(daily_candles, daily_zones, debug=debug)
    if not rejections:
        if debug:
            print(f"  [STORY] No Daily rejection — no storyline")
        return None

    # ─── Factor 2: H4 QM ───
    h4_bull_qm = detect_qm(h4_candles, 'bullish', pair=pair, debug=False)
    h4_bear_qm = detect_qm(h4_candles, 'bearish', pair=pair, debug=False)

    if debug:
        print(f"  [STORY] H4 QMs: "
              f"bullish={bool(h4_bull_qm)} bearish={bool(h4_bear_qm)}")

    # ─── Combine ───
    # Prefer the most recent rejection that has a matching H4 QM
    rejections_sorted = sorted(rejections, key=lambda r: r['candle_index'], reverse=True)

    for rej in rejections_sorted:
        direction = rej['direction']
        qm = h4_bear_qm if direction == 'bearish' else h4_bull_qm
        if not qm:
            continue

        # Age check on H4 QM
        if qm['candles_since_break'] > MAX_QM_AGE_H4:
            if debug:
                print(f"  [STORY] H4 QM too old "
                      f"({qm['candles_since_break']} candles > {MAX_QM_AGE_H4})")
            continue

        if debug:
            print(f"  [STORY] ✅ {direction.upper()} storyline active "
                  f"(Daily rejection + H4 QM)")

        return {
            'storyline': direction,
            'rejection_zone': rej['zone'],
            'rejection_candle': rej['candle'],
            'h4_qm': qm,
        }

    if debug:
        print(f"  [STORY] Rejections found but no matching H4 QM")
    return None
