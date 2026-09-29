"""
BOS Structure Detector

Determines market structure state on any timeframe.

States:
  'bullish' — recent swings show HH (higher highs) + HL (higher lows)
  'bearish' — recent swings show LH (lower highs) + LL (lower lows)
  'ranging' — no clear directional sequence
  'unknown' — insufficient data

Also detects CHoCH (Change of Character): a close beyond the last
structural swing in the opposite direction.
"""

from swing_detector import find_swing_highs, find_swing_lows


LOOKBACK = 60
SWING_LEFT = 2
SWING_RIGHT = 2
MIN_LABELS = 3


def _label_highs(swing_highs):
    labels = []
    for i in range(1, len(swing_highs)):
        if swing_highs[i]['level'] > swing_highs[i-1]['level']:
            labels.append('HH')
        else:
            labels.append('LH')
    return labels


def _label_lows(swing_lows):
    labels = []
    for i in range(1, len(swing_lows)):
        if swing_lows[i]['level'] > swing_lows[i-1]['level']:
            labels.append('HL')
        else:
            labels.append('LL')
    return labels


def _classify(highs_labels, lows_labels):
    rh = highs_labels[-3:]
    rl = lows_labels[-3:]
    bull = sum(1 for x in rh if x == 'HH') + sum(1 for x in rl if x == 'HL')
    bear = sum(1 for x in rh if x == 'LH') + sum(1 for x in rl if x == 'LL')
    if bull >= MIN_LABELS and bull > bear:
        return 'bullish', bull, bear
    if bear >= MIN_LABELS and bear > bull:
        return 'bearish', bull, bear
    return 'ranging', bull, bear


def analyze(candles, debug=False):
    """Analyze candle structure. Returns state dict."""
    if len(candles) < 20:
        return {'state': 'unknown'}

    n = len(candles)
    window_start = max(0, n - LOOKBACK)
    window = candles[window_start:]

    swing_highs = find_swing_highs(window, left=SWING_LEFT, right=SWING_RIGHT)
    swing_lows = find_swing_lows(window, left=SWING_LEFT, right=SWING_RIGHT)

    for s in swing_highs:
        s['index'] += window_start
    for s in swing_lows:
        s['index'] += window_start

    if debug:
        print(f"  [STRUCT] swings: {len(swing_highs)} highs, {len(swing_lows)} lows")

    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return {'state': 'unknown', 'reason': 'insufficient swings'}

    highs_labels = _label_highs(swing_highs)
    lows_labels = _label_lows(swing_lows)
    state, bull, bear = _classify(highs_labels, lows_labels)

    if debug:
        print(f"  [STRUCT] highs={highs_labels[-3:]} lows={lows_labels[-3:]}")
        print(f"  [STRUCT] bull={bull} bear={bear} → {state}")

    result = {
        'state': state,
        'bull_signals': bull,
        'bear_signals': bear,
        'recent_highs': swing_highs[-3:],
        'recent_lows': swing_lows[-3:],
        'highs_labels': highs_labels[-3:],
        'lows_labels': lows_labels[-3:],
    }

    if state == 'bullish':
        hh_idx = [i for i, l in enumerate(highs_labels) if l == 'HH']
        hl_idx = [i for i, l in enumerate(lows_labels) if l == 'HL']
        if hh_idx:
            result['last_hh'] = swing_highs[hh_idx[-1] + 1]
        if hl_idx:
            result['last_hl'] = swing_lows[hl_idx[-1] + 1]
    elif state == 'bearish':
        lh_idx = [i for i, l in enumerate(highs_labels) if l == 'LH']
        ll_idx = [i for i, l in enumerate(lows_labels) if l == 'LL']
        if lh_idx:
            result['last_lh'] = swing_highs[lh_idx[-1] + 1]
        if ll_idx:
            result['last_ll'] = swing_lows[ll_idx[-1] + 1]

    return result


def detect_choch(candles, structure):
    """
    Detect a recent CHoCH.
    Bullish structure → CHoCH = close below last_hl
    Bearish structure → CHoCH = close above last_lh
    """
    state = structure.get('state')
    n = len(candles)

    if state == 'bullish':
        hl = structure.get('last_hl')
        if not hl:
            return None
        for i in range(hl['index'] + 1, n):
            if candles[i]['close'] < hl['level']:
                return {
                    'type': 'bearish_choch',
                    'break_index': i,
                    'break_level': hl['level'],
                    'candles_since': n - 1 - i,
                }
        return None

    if state == 'bearish':
        lh = structure.get('last_lh')
        if not lh:
            return None
        for i in range(lh['index'] + 1, n):
            if candles[i]['close'] > lh['level']:
                return {
                    'type': 'bullish_choch',
                    'break_index': i,
                    'break_level': lh['level'],
                    'candles_since': n - 1 - i,
                }
        return None

    return None
