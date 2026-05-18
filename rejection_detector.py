"""
Rejection Candle Detector – Relaxed with synthetic fallback
"""

def detect_rejection(candles, direction, retest=None, breakout=None, debug=False, min_wick_ratio=0.3):
    if breakout is None:
        if debug: print("Rejection: no breakout → abort")
        return None

    start_idx = breakout.get('break_index', 0)
    if retest and retest.get('index') is not None:
        start_idx = max(start_idx, retest['index'])
    end_idx = len(candles) - 1

    if debug:
        print(f"Rejection: searching candles from index {start_idx} to {end_idx}")

    best_rejection = None
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

        if direction == 'buy':
            if close <= open_price: continue
            lower_wick = min(open_price, close) - low
            wick_ratio = lower_wick / body
            if debug:
                print(f"Rejection: candle {i} buy: body={body:.5f} lower_wick={lower_wick:.5f} ratio={wick_ratio:.2f}")
            if wick_ratio >= min_wick_ratio and wick_ratio > best_ratio:
                best_rejection = {'index': i, 'candle': candle}
                best_ratio = wick_ratio
        else:  # sell
            if close >= open_price: continue
            upper_wick = high - max(open_price, close)
            wick_ratio = upper_wick / body
            if debug:
                print(f"Rejection: candle {i} sell: body={body:.5f} upper_wick={upper_wick:.5f} ratio={wick_ratio:.2f}")
            if wick_ratio >= min_wick_ratio and wick_ratio > best_ratio:
                best_rejection = {'index': i, 'candle': candle}
                best_ratio = wick_ratio

    if best_rejection:
        if debug: print(f"Rejection: found best at idx {best_rejection['index']} ratio {best_ratio:.2f}")
        return best_rejection

    # Fallback: if breakout is very fresh and retest synthetic, create synthetic rejection
    if breakout.get('break_index', 0) >= end_idx - 1 and retest and retest.get('synthetic'):
        if debug:
            print("Rejection: fresh breakout & synthetic retest → using synthetic rejection")
        candle = candles[end_idx]
        return {'index': end_idx, 'candle': candle, 'synthetic': True}

    if debug:
        print("Rejection: no candle met wick ratio threshold")
    return None
