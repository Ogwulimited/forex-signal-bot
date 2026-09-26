"""
MSNR H4 Rejection Detector v2

Changes from v1:
  - Checks the last 3 closed H4 candles for a rejection (was: last 1)
  - Returns the MOST RECENT rejection if multiple exist
  - rejection_index identifies which candle rejected
"""

from zone_filter import PIP_SCALE


TOUCH_TOLERANCE_PIPS = 3
REJECTION_LOOKBACK_CANDLES = 3     # check the last N closed H4 candles


def _pips_to_price(pair, pips):
    return pips * PIP_SCALE.get(pair, 0.0001)


def _check_rejection(candle, zone, direction, pair, tolerance_pips=TOUCH_TOLERANCE_PIPS):
    """Check if a single candle rejected a single zone."""
    tol = _pips_to_price(pair, tolerance_pips)
    zl = zone['level']

    if direction == 'bearish':
        touched = candle['high'] >= (zl - tol)
        closed_below = candle['close'] < zl
        return touched and closed_below
    else:  # bullish
        touched = candle['low'] <= (zl + tol)
        closed_above = candle['close'] > zl
        return touched and closed_above


def detect_h4_rejection(setup, h4_candles, pair, debug=False):
    """
    Scan the last N closed H4 candles for a rejection of the setup's
    entry zone. Returns the most recent rejection found, or None.
    """
    if not setup or not setup.get('entry'):
        return None

    direction = setup.get('direction')
    if not direction:
        direction = setup.get('_storyline')
    if direction not in ('bearish', 'bullish'):
        if debug:
            print(f"  [REJ] No direction — cannot detect")
        return None

    entry_zone = setup['entry']
    n = len(h4_candles)
    if n < 3:
        return None

    # Scan last N candles, most recent first
    start = max(0, n - REJECTION_LOOKBACK_CANDLES)

    if debug:
        print(f"  [REJ] scanning H4 candles {start}..{n-1} "
              f"(entry zone @ {entry_zone['level']:.5f}, direction={direction})")

    for i in range(n - 1, start - 1, -1):
        candle = h4_candles[i]
        if _check_rejection(candle, entry_zone, direction, pair):
            if debug:
                print(f"  [REJ] ✅ rejection at candle {i} "
                      f"(close={candle['close']:.5f})")
            return {
                'active_window': True,
                'rejection_zone': entry_zone,
                'rejection_candle': candle,
                'rejection_index': i,
                'window_h4_index': i + 1,
                'candles_since_rejection': n - 1 - i,
            }

    if debug:
        print(f"  [REJ] no rejection in last {REJECTION_LOOKBACK_CANDLES} candles")
    return None
