"""
Swing high and swing low detector.
Identifies local highs/lows using left/right candle comparison.
"""

def find_swing_highs(candles, left=2, right=2):
    """
    Find all swing highs in the candle list.
    
    Parameters:
    - candles: list of dicts with 'high', 'low', 'close'
    - left: number of candles to look left
    - right: number of candles to look right
    
    Returns:
    - list of dicts with keys: index, level (high price)
    """
    swings = []
    n = len(candles)
    
    for i in range(left, n - right):
        is_swing = True
        # Check left candles
        for j in range(1, left + 1):
            if candles[i]['high'] <= candles[i - j]['high']:
                is_swing = False
                break
        # Check right candles
        if is_swing:
            for j in range(1, right + 1):
                if candles[i]['high'] <= candles[i + j]['high']:
                    is_swing = False
                    break
        if is_swing:
            swings.append({
                'index': i,
                'level': candles[i]['high']
            })
    
    return swings


def find_swing_lows(candles, left=2, right=2):
    """
    Find all swing lows in the candle list.
    
    Parameters:
    - candles: list of dicts with 'high', 'low', 'close'
    - left: number of candles to look left
    - right: number of candles to look right
    
    Returns:
    - list of dicts with keys: index, level (low price)
    """
    swings = []
    n = len(candles)
    
    for i in range(left, n - right):
        is_swing = True
        # Check left candles
        for j in range(1, left + 1):
            if candles[i]['low'] >= candles[i - j]['low']:
                is_swing = False
                break
        # Check right candles
        if is_swing:
            for j in range(1, right + 1):
                if candles[i]['low'] >= candles[i + j]['low']:
                    is_swing = False
                    break
        if is_swing:
            swings.append({
                'index': i,
                'level': candles[i]['low']
            })
    
    return swings
