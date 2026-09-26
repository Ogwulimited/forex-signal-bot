"""
MSNR H1 Confirmation Engine v2

Changes from v1:
  - Confirmation window extended to 2 H4 candles (8 hours) from 1 (4 hours)
  - Window starts at the close of the rejection H4 candle
  - Accepts QM (structure break) or open-close break
"""

from qm_detector import detect_qm


H4_SECONDS = 4 * 3600
WINDOW_H4_CANDLES = 2           # was 1 — now 8 hours of grace


def _epoch(candle):
    return candle.get('datetime', 0)


def _open_close_break(h1_candles, direction):
    """Return the most recent open-close break candle or None."""
    if len(h1_candles) < 2:
        return None

    for i in range(len(h1_candles) - 1, 0, -1):
        prev = h1_candles[i - 1]
        curr = h1_candles[i]
        if direction == 'bearish':
            if curr['close'] < prev['low']:
                return curr
        else:
            if curr['close'] > prev['high']:
                return curr
    return None


def _infer_direction(rejection):
    """Determine trade direction from the rejection zone type + storyline."""
    zt = rejection['rejection_zone']['type']
    storyline = rejection.get('_storyline')
    if storyline:
        return 'bearish' if storyline == 'bearish' else 'bullish'
    return 'bearish' if zt in ('resistance', 'flip') else 'bullish'


def detect_h1_confirmation(rejection, h1_candles, pair, debug=False):
    """
    Given a rejection and the full H1 series, check whether confirmation
    occurred within the open window.
    """
    if not rejection or not rejection.get('active_window'):
        return None

    rej_candle = rejection['rejection_candle']
    rej_epoch = _epoch(rej_candle)
    if not rej_epoch:
        if debug:
            print("  [CONF] rejection candle missing epoch")
        return None

    # Window: opens at close of rejection H4 candle, extends for WINDOW_H4_CANDLES
    window_start = rej_epoch + H4_SECONDS
    window_end = window_start + (WINDOW_H4_CANDLES * H4_SECONDS)

    if debug:
        print(f"  [CONF] window: {window_start} → {window_end} "
              f"({WINDOW_H4_CANDLES} H4 candles)")

    window_h1 = [c for c in h1_candles
                 if _epoch(c) >= window_start and _epoch(c) < window_end]

    if debug:
        print(f"  [CONF] H1 candles in window: {len(window_h1)}")

    if not window_h1:
        if debug:
            print(f"  [CONF] no H1 candles in window")
        return None

    direction = _infer_direction(rejection)

    # Try QM first
    qm = detect_qm(window_h1, direction, pair=pair, debug=False)
    if qm:
        break_epoch = _epoch(qm['break_candle'])
        idx = next((i for i, c in enumerate(window_h1)
                    if _epoch(c) == break_epoch), None)
        if debug:
            print(f"  [CONF] ✅ QM confirmed ({direction})")
        return {
            'confirmed': True,
            'method': 'qm',
            'break_candle': qm['break_candle'],
            'break_index_h1': idx,
            'window_epoch_start': window_start,
            'window_epoch_end': window_end,
        }

    # Fall back to open-close break
    oc = _open_close_break(window_h1, direction)
    if oc:
        idx = next((i for i, c in enumerate(window_h1)
                    if _epoch(c) == _epoch(oc)), None)
        if debug:
            print(f"  [CONF] ✅ Open-close confirmed ({direction})")
        return {
            'confirmed': True,
            'method': 'open_close',
            'break_candle': oc,
            'break_index_h1': idx,
            'window_epoch_start': window_start,
            'window_epoch_end': window_end,
        }

    if debug:
        print(f"  [CONF] no confirmation in window")
    return None
