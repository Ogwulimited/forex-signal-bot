"""
Chop filter to avoid low-range / choppy markets.
"""

def is_choppy(candles, lookback=20, min_range_ratio=0.0005):
    """
    Determine if market is too choppy for entry.
    
    Parameters:
    - candles: list of candle dicts with 'high', 'low'
    - lookback: number of candles to analyze
    - min_range_ratio: minimum (high-low)/price to consider not choppy
    
    Returns:
    - True if choppy (bad), False if not choppy (good)
    """
    if len(candles) < lookback:
        return True
    
    recent = candles[-lookback:]
    highest_high = max(c['high'] for c in recent)
    lowest_low = min(c['low'] for c in recent)
    avg_price = (highest_high + lowest_low) / 2
    range_ratio = (highest_high - lowest_low) / avg_price if avg_price > 0 else 0
    
    return range_ratio < min_range_ratio
