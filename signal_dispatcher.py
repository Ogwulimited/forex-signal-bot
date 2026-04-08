"""
Main entry logic for 5M trade signals.
Combines HTF bias, breakout, retest, rejection, liquidity sweep, and RR.
"""

from market_data import fetch_candles
from breakout_detector import detect_breakout
from retest_detector import detect_retest
from rejection_detector import detect_rejection
from liquidity_sweep_detector import detect_liquidity_sweep
from chop_filter import is_choppy
from rr_calculator import calculate_rr

def generate_signal(bias_data, debug=False, ignore_chop=False, force_breakout=False, force_sweep=False):
    """
    Generate a 5M trade signal if all conditions are met.
    
    Parameters:
    - bias_data: dict from mtf_bias_engine (must contain pair, bias_4h, bias_1h, aligned)
    - debug: print detailed logs
    - ignore_chop: bypass chop filter for testing
    - force_breakout: force breakout detection to simulate breakout for debugging
    - force_sweep: force liquidity sweep detection to simulate sweep for debugging
    
    Returns:
    - signal dict with keys: pair, direction, entry, sl, tp, timeframe, rr
    - None if no signal
    """
    
    pair = bias_data['pair']
    
    # 1. Check HTF alignment
    if not bias_data.get('aligned', False):
        if debug:
            print(f"Signal rejected: HTF not aligned (4H={bias_data.get('bias_4h')}, 1H={bias_data.get('bias_1h')})")
        return None
    
    # Determine direction from HTF bias (both same because aligned)
    if bias_data['bias_4h'] == 'bullish':
        direction = 'buy'
    elif bias_data['bias_4h'] == 'bearish':
        direction = 'sell'
    else:
        if debug:
            print("Signal rejected: neutral bias")
        return None
    
    if debug:
        print(f"5M pipeline started for {pair} | direction={direction}")
    
    # 2. Fetch 5M candles
    candles = fetch_candles(pair, interval='5min', outputsize=100)
    if not candles or len(candles) < 30:
        if debug:
            print("Signal rejected: insufficient 5M candles")
        return None
    
    if debug:
        print(f"Fetched {len(candles)} x 5M candles for {pair}")
    
    # 3. Chop filter (optional)
    if not ignore_chop:
        if is_choppy(candles, lookback=20, min_range_ratio=0.0005):
            if debug:
                print("Signal rejected: market too choppy")
            return None
    else:
        if debug:
            print("Chop filter bypassed for testing.")
    
    # 4. Breakout detection
    breakout = detect_breakout(
        candles,
        direction,
        breakout_window=5,
        min_bars_after_swing=3,
        debug=debug,
        force_breakout=force_breakout
    )
    if not breakout:
        if debug:
            print("Signal rejected: no breakout detected.")
        return None
    
    if debug and breakout.get('forced'):
        print("NOTE: Using FORCED breakout for debugging.")
    
    # 5. Retest detection
    retest = detect_retest(candles, breakout, direction, tolerance_ratio=0.0003, max_retest_bars=10, debug=debug)
    if not retest:
        if debug:
            print("Signal rejected: no retest detected.")
        return None
    
    # 6. Rejection detection
    rejection = detect_rejection(candles, direction, debug=debug)
    if not rejection:
        if debug:
            print("Signal rejected: no rejection candle.")
        return None
    
    # 7. Liquidity sweep detection
    sweep = detect_liquidity_sweep(candles, direction, lookback=20, debug=debug, force_sweep=force_sweep)
    if not sweep:
        if debug:
            print("Signal rejected: no liquidity sweep.")
        return None
    
    if debug and sweep.get('forced'):
        print("NOTE: Using FORCED liquidity sweep for debugging.")
    
    # 8. Calculate RR and trade levels
    trade = calculate_rr(candles, direction, rejection, sweep, debug=debug)
    if not trade or trade.get('rr', 0) < 2.0:
        if debug:
            print(f"Signal rejected: RR insufficient (got {trade.get('rr', 0) if trade else 'None'})")
        return None
    
    # 9. Build final signal
    signal = {
        'pair': pair,
        'direction': direction,
        'entry': trade['entry'],
        'sl': trade['sl'],
        'tp': trade['tp'],
        'timeframe': '5M',
        'rr': trade['rr']
    }
    
    if debug:
        print(f"Signal generated: {signal}")
    
    return signal
