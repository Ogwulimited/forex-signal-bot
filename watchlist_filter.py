"""
HTF Watchlist Filter
Determines if a pair passes the higher-timeframe criteria.
"""

def passes_watchlist(bias_data):
    """
    Check if a pair should be on the HTF watchlist.
    
    Parameters:
    - bias_data: dict from mtf_bias_engine.get_mtf_bias()
    
    Returns:
    - True if all criteria met, else False
    """
    if not bias_data.get('aligned', False):
        return False
    
    # Relaxed thresholds for quantity over quality
    STRENGTH_MIN = 2          # Was 3
    RANGE_RATIO_4H_MIN = 0.002   # Was 0.003
    RANGE_RATIO_1H_MIN = 0.001   # Was 0.0015
    
    if bias_data['strength_4h'] < STRENGTH_MIN:
        return False
    if bias_data['strength_1h'] < STRENGTH_MIN:
        return False
    if bias_data['range_ratio_4h'] < RANGE_RATIO_4H_MIN:
        return False
    if bias_data['range_ratio_1h'] < RANGE_RATIO_1H_MIN:
        return False
    
    return True
