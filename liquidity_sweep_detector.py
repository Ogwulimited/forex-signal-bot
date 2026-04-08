"""
Liquidity sweep detector.
Identifies when price sweeps a recent low (for buy) or recent high (for sell).
"""

def detect_liquidity_sweep(candles, direction, lookback=20, debug=False):
    """
    Detect if price swept liquidity before potential entry.
    
    Parameters:
    - candles: list of candle dicts
    - direction: 'buy' or 'sell'
    - lookback: number of candles to check for sweep level
    - debug: print logs
    
    Returns:
    - dict with keys: level, sweep_index, type, or None
    """
    if len(candles) < lookback + 5:
        if debug:
            print("Liquidity sweep: insufficient candles")
        return None
    
    # Look at recent candles (last 10) for sweep
    recent_start = max(0, len(candles) - 10)
    
    if direction == 'buy':
        # Need sweep of a recent low
        # Find the lowest low in lookback period (excluding the very last candle)
        lookback_candles = candles[-lookback-1:-1] if len(candles) > lookback+1 else candles[:-1]
        if not lookback_candles:
            return None
        recent_low = min(c['low'] for c in lookback_candles)
        
        # Check if any recent candle swept below that low and then closed above it
        for i in range(recent_start, len(candles)):
            candle = candles[i]
            if candle['low'] < recent_low and candle['close'] > recent_low:
                if debug:
                    print(f"Liquidity sweep: buy sweep detected at index {i}, low={candle['low']}, swept level={recent_low}")
                return {
                    'level': recent_low,
                    'sweep_index': i,
                    'type': 'buy_sweep',
                    'candle': candle
                }
    else:  # sell
        # Need sweep of a recent high
        lookback_candles = candles[-lookback-1:-1] if len(candles) > lookback+1 else candles[:-1]
        if not lookback_candles:
            return None
        recent_high = max(c['high'] for c in lookback_candles)
        
        for i in range(recent_start, len(candles)):
            candle = candles[i]
            if candle['high'] > recent_high and candle['close'] < recent_high:
                if debug:
                    print(f"Liquidity sweep: sell sweep detected at index {i}, high={candle['high']}, swept level={recent_high}")
                return {
                    'level': recent_high,
                    'sweep_index': i,
                    'type': 'sell_sweep',
                    'candle': candle
                }
    
    if debug:
        print(f"Liquidity sweep: no sweep detected for {direction}")
    return None
