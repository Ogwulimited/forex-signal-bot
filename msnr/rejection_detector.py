"""
MSNR H4 Rejection Detector

Given a classified setup (entry zone + storyline direction) and the
working-timeframe (H4) candles, detects whether a completed H4 candle
has just rejected the entry zone.

Rejection definition (from Session 4 Q&A):
  - Bearish rejection: candle.high >= zone.level AND candle.close < zone.level
  - Bullish rejection: candle.low <= zone.level AND candle.close > zone.level

Timing (from Session 4 Q&A):
  - Once a rejection is detected on a CLOSED H4 candle, the entry
    window is the NEXT H4 candle.
  - H1 confirmation must occur within that next candle's duration.
  - After the next H4 candle closes without confirmation, window is dead.
"""

from zone_filter import PIP_SCALE


# Tolerance for "wick touched the zone" — allows price to get within
# a few pips of the zone level without requiring exact touch.
TOUCH_TOLERANCE_PIPS = 3


def _pips_to_price(pair, pips):
    return pips * PIP_SCALE.get(pair, 0.0001)


def _check_rejection(candle, zone, direction, pair, tolerance_pips=TOUCH_TOLERANCE_PIPS):
    """
    Check if a single candle rejected a single zone.
    Returns True/False.
    """
    tol = _pips_to_price(pair, tolerance_pips)
    zl = zone['level']

    if direction == 'bearish':
        # Price must have wicked up into/through the resistance zone
        # AND closed below it.
        touched = candle['high'] >= (zl - tol)
        closed_below = candle['close'] < zl
        return touched and closed_below

    else:  # bullish
        touched = candle['low'] <= (zl + tol)
        closed_above = candle['close'] > zl
        return touched and closed_above


def detect_h4_rejection(setup, h4_candles, pair, debug=False):
    """
    Scan the most recent COMPLETED H4 candle(s) for a rejection of the
    setup's entry zone.

    Parameters:
    - setup: dict from zone_classifier with 'entry' zone
    - h4_candles: list of H4 candle dicts (last one may be forming)
    - pair: pair name
    - debug: print reasoning

    Returns:
    - dict or None:
      {
        'active_window': bool,
        'rejection_zone': {...},
        'rejection_candle': {...},
        'rejection_index': int,
        'window_h4_index': int,     # index of the H4 candle now forming
      }
    """
    if not setup or not setup.get('entry'):
        return None

    direction = setup.get('direction')  # set by classifier, or fallback below
    # The classifier returns 'storyline' at top level; setups don't carry it.
    # We pass direction via a wrapping dict from the caller.
    if not direction:
        direction = setup.get('_storyline')
    if direction not in ('bearish', 'bullish'):
        if debug:
            print(f"  [REJ] No direction on setup — cannot detect")
        return None

    entry_zone = setup['entry']
    n = len(h4_candles)
    if n < 3:
        return None

    # The most recently CLOSED candle is at index n-1 (if the exchange
    # has already moved on) or we treat index n-1 as closed. For simplicity
    # in a scan-based bot, we treat index n-1 as the last closed candle
    # and index n as the currently-forming one. In practice the loop is
    # run right after an H4 close, so index n-1 is the just-closed candle.

    # Check rejection on the most recent completed candle
    last_closed = h4_candles[-1]
    rejected = _check_rejection(last_closed, entry_zone, direction, pair)

    if debug:
        print(f"  [REJ] last H4 close={last_closed['close']:.5f} "
              f"high={last_closed['high']:.5f} low={last_closed['low']:.5f}")
        print(f"  [REJ] entry zone @ {entry_zone['level']:.5f} | "
              f"rejected={rejected}")

    if not rejected:
        return None

    if debug:
        print(f"  [REJ] ✅ rejection active on last closed H4 candle")

    return {
        'active_window': True,
        'rejection_zone': entry_zone,
        'rejection_candle': last_closed,
        'rejection_index': n - 1,
        'window_h4_index': n,   # the currently-forming candle is the window
  }
