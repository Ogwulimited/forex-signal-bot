"""
Rejection Candle Detector – Relaxed
Detects bullish/bearish rejection candles near a retest level.
- Buy: bullish body, lower wick/body >= min_wick_ratio
- Sell: bearish body, upper wick/body >= min_wick_ratio
"""

def detect_rejection(candles, direction, retest=None, breakout=None, debug=False, min_wick_ratio=0.3):
    """
    Find a rejection candle after a retest.

    Parameters:
    - candles: list of dicts (high, low, close)
    - direction: 'buy' or 'sell'
    - retest: dict from detect_retest (contains 'index')
    - breakout: dict from detect_breakout (contains 'break_index')
    - debug: print detailed logs
    - min_wick_ratio: minimum lower/upper wick relative to body (default 0.3)

    Returns:
    - dict with 'index', 'candle', or None
    """
    if breakout is None:
        if debug:
            print("Rejection: no breakout provided → abort")
        return None

    start_idx = breakout.get('break_index', 0)
    if retest and 'index' in retest:
        start_idx = max(start_idx, retest['index'])
    end_idx = len(candles) - 1

    if debug:
        print(f"Rejection: searching candles from index {start_idx} to {end_idx}")

    best_rejection = None
    best_ratio = 0

    for i in range(start_idx, end_idx + 1):
        candle = candles[i]
        open_price = candle.get('open', candle['close'])  # fallback if no open
        high = candle['high']
        low = candle['low']
        close = candle['close']

        body = abs(close - open_price)
        if body == 0:
            continue

        if direction == 'buy':
            # Bullish rejection: close > open, long lower wick
            if close <= open_price:
                continue
            lower_wick = min(open_price, close) - low
            wick_ratio = lower_wick / body
            if debug:
                print(f"Rejection: candle {i} buy check: body={body:.5f}, lower_wick={lower_wick:.5f}, ratio={wick_ratio:.2f}")
            if wick_ratio >= min_wick_ratio:
                if wick_ratio > best_ratio:
                    best_rejection = {'index': i, 'candle': candle}
                    best_ratio = wick_ratio
        else:  # sell
            # Bearish rejection: close < open, long upper wick
            if close >= open_price:
                continue
            upper_wick = high - max(open_price, close)
            wick_ratio = upper_wick / body
            if debug:
                print(f"Rejection: candle {i} sell check: body={body:.5f}, upper_wick={upper_wick:.5f}, ratio={wick_ratio:.2f}")
            if wick_ratio >= min_wick_ratio:
                if wick_ratio > best_ratio:
                    best_rejection = {'index': i, 'candle': candle}
                    best_ratio = wick_ratio

    if best_rejection:
        if debug:
            print(f"Rejection: found best rejection at index {best_rejection['index']} with wick ratio {best_ratio:.2f}")
        return best_rejection

    if debug:
        print("Rejection: no candle met wick ratio threshold")
    return None
