"""
Liquidity Sweep Detector
Detects liquidity grabs:
- Buy: price sweeps below a recent swing low, then recovers (close above).
- Sell: price sweeps above a recent swing high, then recovers (close below).
"""

from swing_detector import find_swing_lows, find_swing_highs

def detect_liquidity_sweep(candles, direction, breakout=None, retest=None, lookback=20, debug=False, force_sweep=False):
    """
    Detect a liquidity sweep.

    Parameters:
    - candles: list of candle dicts (must include 'high','low','close')
    - direction: 'buy' or 'sell'
    - breakout: dict from detect_breakout (contains 'index', 'level')
    - retest: dict from detect_retest (contains 'index')
    - lookback: number of candles for swing detection
    - debug: if True, print detailed reasoning
    - force_sweep: if True, always return a dummy sweep

    Returns:
    - dict with sweep details or None
    """
    if force_sweep:
        if debug:
            print("  [SWEEP] force_sweep=True → returning dummy sweep")
        return {
            'index': len(candles) - 1,
            'price': candles[-1]['low'] if direction == 'buy' else candles[-1]['high'],
            'swing_index': 0,
            'forced': True
        }

    if breakout is None:
        if debug:
            print("  [SWEEP] No breakout provided → abort")
        return None

    breakout_index = breakout['index']
    start_idx = breakout_index
    end_idx = len(candles) - 1

    if end_idx - start_idx < 2:
        if debug:
            print(f"  [SWEEP] Not enough candles after breakout (start={start_idx}, end={end_idx})")
        return None

    # Find swings using your original swing detector
    # For buy sweep we need swing lows; for sell sweep we need swing highs
    if direction == 'buy':
        swings = find_swing_lows(candles, left=2, right=2)
        if debug:
            print(f"  [SWEEP] Found {len(swings)} swing lows")
        # Filter swings that occurred before breakout
        prior_swings = [s for s in swings if s['index'] < breakout_index]
        if not prior_swings:
            if debug:
                print("  [SWEEP] No prior swing lows found before breakout")
            return None
        target_swing = max(prior_swings, key=lambda x: x['index'])
        swing_level = target_swing['level']
        swing_idx = target_swing['index']

        if debug:
            print(f"  [SWEEP] Buy sweep check: target swing low {swing_level:.5f} at index {swing_idx}")

        for i in range(start_idx, end_idx + 1):
            if candles[i]['low'] < swing_level:
                for j in range(i + 1, end_idx + 1):
                    if candles[j]['close'] > swing_level:
                        if debug:
                            print(f"  [SWEEP] ✅ BUY SWEEP DETECTED: dip at {candles[i]['low']:.5f} (idx {i}), recovery close {candles[j]['close']:.5f} (idx {j})")
                        return {
                            'index': i,
                            'price': candles[i]['low'],
                            'swing_index': swing_idx,
                            'forced': False
                        }
        if debug:
            print("  [SWEEP] ❌ No valid buy sweep (no dip below swing low with recovery)")

    else:  # direction == 'sell'
        swings = find_swing_highs(candles, left=2, right=2)
        if debug:
            print(f"  [SWEEP] Found {len(swings)} swing highs")
        prior_swings = [s for s in swings if s['index'] < breakout_index]
        if not prior_swings:
            if debug:
                print("  [SWEEP] No prior swing highs found before breakout")
            return None
        target_swing = max(prior_swings, key=lambda x: x['index'])
        swing_level = target_swing['level']
        swing_idx = target_swing['index']

        if debug:
            print(f"  [SWEEP] Sell sweep check: target swing high {swing_level:.5f} at index {swing_idx}")

        for i in range(start_idx, end_idx + 1):
            if candles[i]['high'] > swing_level:
                for j in range(i + 1, end_idx + 1):
                    if candles[j]['close'] < swing_level:
                        if debug:
                            print(f"  [SWEEP] ✅ SELL SWEEP DETECTED: spike at {candles[i]['high']:.5f} (idx {i}), recovery close {candles[j]['close']:.5f} (idx {j})")
                        return {
                            'index': i,
                            'price': candles[i]['high'],
                            'swing_index': swing_idx,
                            'forced': False
                        }
        if debug:
            print("  [SWEEP] ❌ No valid sell sweep (no spike above swing high with recovery)")

    return None
