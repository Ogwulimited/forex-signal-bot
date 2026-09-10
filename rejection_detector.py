"""
Strict Rejection Detector – requires strong wick.
"""

def detect_rejection(candles, direction, retest=None, breakout=None, debug=False, min_wick_ratio=0.6):
    if breakout is None:
        return None

    start_idx = breakout.get('break_index', 0)
    if retest and 'index' in retest:
        start_idx = max(start_idx, retest['index'])
    end_idx = len(candles) - 1

    best = None
    best_ratio = 0

    for i in range(start_idx, end_idx + 1):
        candle = candles[i]
        open_price = candle.get('open', candle['close'])
        high = candle['high']
        low = candle['low']
        close = candle['close']
        body = abs(close - open_price)
        if body == 0:
            continue

        if direction == 'buy' and close > open_price:
            lower_wick = min(open_price, close) - low
            ratio = lower_wick / body
            if ratio >= min_wick_ratio and ratio > best_ratio:
                best = {'index': i, 'candle': candle}
                best_ratio = ratio
        elif direction == 'sell' and close < open_price:
            upper_wick = high - max(open_price, close)
            ratio = upper_wick / body
            if ratio >= min_wick_ratio and ratio > best_ratio:
                best = {'index': i, 'candle': candle}
                best_ratio = ratio

    return best
