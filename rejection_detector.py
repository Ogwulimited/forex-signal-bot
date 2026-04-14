"""
Rejection candle detector – looks at candles around retest/breakout.
"""

def detect_rejection(candles, direction, retest=None, breakout=None, debug=False):
    """
    Detect a rejection candle in the direction of the trade.
    Looks at candles from breakout to recent.
    
    Parameters:
    - candles: list of candle dicts
    - direction: 'buy' or 'sell'
    - retest: retest dict (optional, for context)
    - breakout: breakout dict (optional)
    - debug: print logs
    """
    if len(candles) < 5:
        if debug:
            print("Rejection: insufficient candles")
        return None
    
    # Determine search range: from breakout index to last candle
    start_idx = 0
    if breakout and breakout.get('break_index') is not None:
        start_idx = max(0, breakout['break_index'])
    else:
        start_idx = max(0, len(candles) - 10)  # fallback last 10
    
    if debug:
        print(f"Rejection: searching candles from index {start_idx} to {len(candles)-1}")
    
    for i in range(start_idx, len(candles)):
        candle = candles[i]
        body = abs(candle['close'] - candle['open'])
        if body == 0:
            continue
        
        if direction == 'buy':
            # Bullish rejection: lower wick large relative to body
            lower_wick = min(candle['open'], candle['close']) - candle['low']
            wick_ratio = lower_wick / body if body > 0 else 0
            if wick_ratio >= 0.5:
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
        print("Rejection: no rejection candle found in search range")
    return None
