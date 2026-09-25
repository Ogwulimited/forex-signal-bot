"""
MSNR Storyline Engine v3

Two-factor test for Daily storyline:
  Factor 1: Daily rejection of a Daily zone
  Factor 2: H4 QM in the matching direction

Changes from v2:
  - Wick overshoot filter REMOVED (was killing valid rejections on
    Daily candles, whose wick ranges are naturally wider than H4/H1)
  - Closest-zone-per-direction-per-candle logic retained (this alone
    eliminates mid-range noise)
  - QM timing check retained (QM must be at or after Daily rejection)
"""

from zone_detector import detect_all_zones
from zone_filter import filter_zones
from qm_detector import detect_qm


REJECTION_LOOKBACK_DAYS = 3
MAX_QM_AGE_H4 = 12               # 48 hours


def _check_daily_rejection(daily_candles, daily_zones, pair, debug=False):
    """
    For each recent Daily candle, find the closest zone rejected per direction.
    Returns at most 1 bearish + 1 bullish rejection per candle.
    """
    rejections = []
    n = len(daily_candles)
    start = max(0, n - REJECTION_LOOKBACK_DAYS)

    for i in range(start, n):
        candle = daily_candles[i]

        # ---- Bearish: candle wicked into a resistance, closed below ----
        bear_candidates = [
            z for z in daily_zones
            if z['type'] in ('resistance', 'flip')
            and candle['high'] >= z['level']
            and candle['close'] < z['level']
        ]
        if bear_candidates:
            # Closest to close = highest zone level that still fits the criteria
            best = max(bear_candidates, key=lambda z: z['level'])
            rejections.append({
                'direction': 'bearish',
                'zone': best,
                'candle_index': i,
                'candle': candle,
            })

        # ---- Bullish: candle wicked into a support, closed above ----
        bull_candidates = [
            z for z in daily_zones
            if z['type'] in ('support', 'flip')
            and candle['low'] <= z['level']
            and candle['close'] > z['level']
        ]
        if bull_candidates:
            best = min(bull_candidates, key=lambda z: z['level'])
            rejections.append({
                'direction': 'bullish',
                'zone': best,
                'candle_index': i,
                'candle': candle,
            })

    if debug:
        print(f"  [STORY] Daily rejections found: {len(rejections)}")
        for r in rejections:
            print(f"    {r['direction']:>8} via {r['zone']['type']} "
                  f"@ {r['zone']['level']:.5f} (day idx {r['candle_index']})")

    return rejections


def _candle_epoch(candle):
    """Extract epoch from a candle dict; return 0 if missing."""
    return candle.get('datetime', 0)


def detect_daily_storyline(pair, daily_candles, h4_candles, debug=False):
    """
    Detect the currently active Daily storyline.
    """
    if len(daily_candles) < 30 or len(h4_candles) < 30:
        return None

    # ─── Factor 1: Daily rejection ───
    daily_zones_raw = detect_all_zones(daily_candles, min_open_close_run=2, debug=False)
    daily_zones = filter_zones(daily_zones_raw, daily_candles, pair, debug=False)

    if debug:
        print(f"  [STORY] Daily zones (filtered): {len(daily_zones)}")

    rejections = _check_daily_rejection(daily_candles, daily_zones, pair, debug=debug)
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
    rejections_sorted = sorted(rejections,
                               key=lambda r: r['candle_index'],
                               reverse=True)

    for rej in rejections_sorted:
        direction = rej['direction']
        qm = h4_bear_qm if direction == 'bearish' else h4_bull_qm
        if not qm:
            continue

        if qm['candles_since_break'] > MAX_QM_AGE_H4:
            if debug:
                print(f"  [STORY] {direction} QM too old "
                      f"({qm['candles_since_break']} H4 candles)")
            continue

        # Timing: QM must be at or after the rejection candle
        rej_epoch = _candle_epoch(rej['candle'])
        qm_epoch = _candle_epoch(qm['break_candle'])
        if qm_epoch and rej_epoch and qm_epoch < rej_epoch:
            if debug:
                print(f"  [STORY] {direction} QM predates rejection — skip")
            continue

        if debug:
            print(f"  [STORY] ✅ {direction.upper()} storyline active")

        return {
            'storyline': direction,
            'rejection_zone': rej['zone'],
            'rejection_candle': rej['candle'],
            'rejection_index': rej['candle_index'],
            'h4_qm': qm,
        }

    if debug:
        print(f"  [STORY] No matching rejection + QM pair")
    return None
