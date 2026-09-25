"""
MSNR Zone Detector

Detects the four core MSNR zone types:
  1. A (resistance)     — bullish candle followed by bearish candle
  2. V (support)        — bearish candle followed by bullish candle
  3. Open-Close level   — two or more consecutive same-type candles
                          Zone = midpoint of (open of first, close of last)

Zone levels are based on CLOSING PRICES ONLY (MSNR Golden Rule).
No wicks. No opens. Only closes.

Output: list of zone dicts, each with:
  - type: 'support' | 'resistance'
  - pattern: 'A' | 'V' | 'open_close'
  - level: price (float)
  - index: candle index where the zone was defined
  - candle: the defining candle
"""


def _is_bullish(candle):
    return candle['close'] > candle['open']


def _is_bearish(candle):
    return candle['close'] < candle['open']


def detect_av_zones(candles, debug=False):
    """
    Detect A and V formations on a candle series.
    
    A (resistance) = bullish candle → bearish candle. Zone = bullish candle's close.
    V (support)    = bearish candle → bullish candle. Zone = bearish candle's close.
    """
    zones = []
    for i in range(1, len(candles)):
        prev = candles[i - 1]
        curr = candles[i]

        prev_bull = _is_bullish(prev)
        prev_bear = _is_bearish(prev)
        curr_bull = _is_bullish(curr)
        curr_bear = _is_bearish(curr)

        # A formation: bullish → bearish
        if prev_bull and curr_bear:
            zones.append({
                'type': 'resistance',
                'pattern': 'A',
                'level': prev['close'],
                'index': i - 1,
                'candle': prev,
            })

        # V formation: bearish → bullish
        elif prev_bear and curr_bull:
            zones.append({
                'type': 'support',
                'pattern': 'V',
                'level': prev['close'],
                'index': i - 1,
                'candle': prev,
            })

    if debug:
        a_count = sum(1 for z in zones if z['pattern'] == 'A')
        v_count = sum(1 for z in zones if z['pattern'] == 'V')
        print(f"  [ZONE] A/V detection: {a_count} A (resistance), {v_count} V (support)")

    return zones


def detect_open_close_zones(candles, min_run=2, debug=False):
    """
    Detect open-close levels: runs of min_run or more same-type candles.
    Zone level = midpoint of (open of first candle, close of last candle).
    """
    zones = []
    n = len(candles)
    if n < min_run:
        return zones

    i = 0
    while i < n:
        c = candles[i]
        is_bull = _is_bullish(c)
        is_bear = _is_bearish(c)
        if not (is_bull or is_bear):
            i += 1
            continue

        # Extend run while same direction
        j = i
        while j + 1 < n:
            nxt = candles[j + 1]
            if is_bull and not _is_bullish(nxt):
                break
            if is_bear and not _is_bearish(nxt):
                break
            j += 1

        run_length = j - i + 1
        if run_length >= min_run:
            first = candles[i]
            last = candles[j]
            midpoint = (first['open'] + last['close']) / 2.0
            zones.append({
                'type': 'support' if is_bull else 'resistance',
                'pattern': 'open_close',
                'level': midpoint,
                'index': j,           # index of last candle in the run
                'run_length': run_length,
                'first_index': i,
                'last_index': j,
                'first_open': first['open'],
                'last_close': last['close'],
            })

        i = j + 1

    if debug:
        print(f"  [ZONE] Open-close detection: {len(zones)} levels "
              f"(min_run={min_run})")

    return zones


def detect_all_zones(candles, min_open_close_run=2, debug=False):
    """
    Run all zone detectors and return a combined list.
    Each zone dict is tagged with 'pattern' so downstream logic can
    distinguish A / V from open-close levels.
    """
    zones = []
    zones.extend(detect_av_zones(candles, debug=debug))
    zones.extend(detect_open_close_zones(candles, min_run=min_open_close_run,
                                          debug=debug))

    if debug:
        print(f"  [ZONE] Total zones detected: {len(zones)}")

    return zones
