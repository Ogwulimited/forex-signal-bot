"""
MSNR H1 Confirmation Engine

After an H4 rejection opens the entry window, we wait for an H1 break
in the trade direction. Confirmation can be either:

  - Structure break (QM) — the stronger signal
  - Open-close break — a candle closes beyond the prior candle's range
    in the trade direction — the softer signal

Window (from Session 4 Q&A):
  The confirmation must occur within the NEXT H4 candle after the
  rejection candle closes. If 4 hours elapse with no confirmation,
  the setup dies.

Session 4 Topic 21:
  "for storylines it has to be a break of structure on one time frame
   lower, but for a confirmation entry on the H4 and H1 it could even
   be an open close"
"""

from zone_filter import PIP_SCALE
from qm_detector import detect_qm


H4_SECONDS = 4 * 3600           # 14400 seconds per H4 candle
WINDOW_H4_CANDLES = 1           # exactly one H4 candle of grace


def _epoch(candle):
    """Extract epoch from candle dict; 0 if missing."""
    return candle.get('datetime', 0)


def _open_close_break(h1_candles, direction):
    """
    Look for an open-close break on the most recent H1 candles.
    An open-close break occurs when a candle closes beyond the
    prior candle's range in the trade direction.

    Returns the break candle dict or None.
    """
    if len(h1_candles) < 2:
        return None

    # Examine candles from most recent backward (prefer fresh breaks)
    for i in range(len(h1_candles) - 1, 0, -1):
        prev = h1_candles[i - 1]
        curr = h1_candles[i]

        if direction == 'bearish':
            if curr['close'] < prev['low']:
                return curr
        else:  # bullish
            if curr['close'] > prev['high']:
                return curr
    return None


def _qm_break(h1_candles, direction, pair):
    """
    Look for an H1 QM in the trade direction.
    Returns the QM dict or None.
    """
    return detect_qm(h1_candles, direction, pair=pair, debug=False)


def detect_h1_confirmation(rejection, h1_candles, pair, debug=False):
    """
    Given a rejection (from rejection_detector) and the H1 candles,
    check whether confirmation has occurred within the open window.

    Parameters:
    - rejection: dict from detect_h4_rejection
    - h1_candles: list of H1 candle dicts (most recent last)
    - pair: pair name
    - debug: print reasoning

    Returns:
    - dict or None:
      {
        'confirmed': True,
        'method': 'qm' | 'open_close',
        'break_candle': {...},
        'break_index_h1': int,
        'window_epoch_start': epoch,
        'window_epoch_end': epoch,
      }
    """
    if not rejection or not rejection.get('active_window'):
        return None

    rej_candle = rejection['rejection_candle']
    rej_epoch = _epoch(rej_candle)
    if not rej_epoch:
        if debug:
            print("  [CONF] rejection candle missing epoch")
        return None

    # Window opens at the close of the rejection H4 candle
    window_start = rej_epoch + H4_SECONDS
    window_end = window_start + (WINDOW_H4_CANDLES * H4_SECONDS)

    if debug:
        print(f"  [CONF] window: {window_start} → {window_end} "
              f"(rejection close + 1 H4)")

    # Filter H1 candles to those inside the window
    window_h1 = [c for c in h1_candles
                 if _epoch(c) >= window_start and _epoch(c) < window_end]

    if debug:
        print(f"  [CONF] H1 candles in window: {len(window_h1)}")
        if window_h1:
            first_e = _epoch(window_h1[0])
            last_e = _epoch(window_h1[-1])
            print(f"  [CONF] window H1 epochs: {first_e} → {last_e}")

    if not window_h1:
        if debug:
            print(f"  [CONF] window not yet started or no H1 candles in range")
        return None

    # Try QM first (stronger signal)
    qm = _qm_break(window_h1, rejection['rejection_zone']['type'] == 'resistance'
                   and 'bearish' or 'bullish', pair)
    # Determine direction from rejection structure
    # We can infer: rejection was against a resistance → bearish trade
    #                rejection was against a support → bullish trade
    trade_direction = 'bearish' if _is_bearish_rejection(rejection) else 'bullish'

    qm = _qm_break(window_h1, trade_direction, pair)

    if qm:
        # Find the QM's candle in window_h1
        break_epoch = _epoch(qm['break_candle'])
        idx = next((i for i, c in enumerate(window_h1)
                    if _epoch(c) == break_epoch), None)
        if debug:
            print(f"  [CONF] ✅ QM break confirmed ({trade_direction})")
        return {
            'confirmed': True,
            'method': 'qm',
            'break_candle': qm['break_candle'],
            'break_index_h1': idx,
            'window_epoch_start': window_start,
            'window_epoch_end': window_end,
        }

    # Fall back to open-close break
    oc = _open_close_break(window_h1, trade_direction)
    if oc:
        idx = next((i for i, c in enumerate(window_h1)
                    if _epoch(c) == _epoch(oc)), None)
        if debug:
            print(f"  [CONF] ✅ Open-close break confirmed ({trade_direction})")
        return {
            'confirmed': True,
            'method': 'open_close',
            'break_candle': oc,
            'break_index_h1': idx,
            'window_epoch_start': window_start,
            'window_epoch_end': window_end,
        }

    if debug:
        print(f"  [CONF] no confirmation yet in window")
    return None


def _is_bearish_rejection(rejection):
    """
    A rejection is bearish if the zone is resistance or flip.
    Bullish if the zone is support.
    """
    zt = rejection['rejection_zone']['type']
    return zt in ('resistance', 'flip') and rejection.get('_storyline') == 'bearish'
