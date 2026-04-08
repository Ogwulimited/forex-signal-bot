"""
Rejection candle detector.
Finds candles that show rejection of a level (long wick opposite to direction).
"""

def detect_rejection(candles, direction, debug=False):
    """
    Detect a rejection candle in the direction of the trade.
    
    Parameters:
    - candles: list of candle dicts with 'open', 'high', 'low', 'close'
    - direction: 'buy' or 'sell'
    - debug: print logs
    
    Returns:
    - dict with keys: index, type, body, wick_ratio, or None if not found
    """
    if len(candles) < 5:
        if debug:
            print("Rejection: insufficient candles")
        return None
    
    # Look at the last 3 candles for rejection
    start_idx = max(0, len(candles) - 3)
    
    for i in range(start_idx, len(candles)):
        candle = candles[i]
        body = abs(candle['close'] - candle['open'])
        if body == 0:
            continue
        
        if direction == 'buy':
            # Bullish rejection: lower wick should be large relative to body
            lower_wick = min(candle['open'], candle['close']) - candle['low']
            wick_ratio = lower_wick / body if body > 0 else 0
            if wick_ratio >= 0.5:  # Lower wick at least half of body
                if debug:
                    print(f"Rejection: found bullish rejection at index {i}, wick_ratio={wick_ratio:.2f}")
                return {
                    'index': i,
                    'type': 'bullish_rejection',
                    'body': body,
                    'wick_ratio': wick_ratio,
                    'candle': candle
                }
        else:  # sell
            # Bearish rejection: upper wick large relative to body
            upper_wick = candle['high'] - max(candle['open'], candle['close'])
            wick_ratio = upper_wick / body if body > 0 else 0
            if wick_ratio >= 0.5:
                if debug:
                    print(f"Rejection: found bearish rejection at index {i}, wick_ratio={wick_ratio:.2f}")
                return {
                    'index': i,
                    'type': 'bearish_rejection',
                    'body': body,
                    'wick_ratio': wick_ratio,
                    'candle': candle
                }
    
    if debug:
        print("Rejection: no rejection candle found in last 3 candles")
    return None
