"""
Liquidity Sweep Detector

Detects liquidity grabs:
- Buy setup: price sweeps below a recent swing low, then recovers (close above).
- Sell setup: price sweeps above a recent swing high, then recovers (close below).

This version includes:
- Debug logging (prints why sweep failed or succeeded)
- More lenient parameters (adjustable)
- Option to use force_sweep override (default False for testing)
"""

from swing_detector import find_swings

def detect_liquidity_sweep(candles, direction, breakout_index=None, retest_index=None, force_sweep=False, debug=True):
    """
    Detect a liquidity sweep.

    Parameters:
    - candles: list of candle dicts (must include 'high','low','close')
    - direction: 'buy' or 'sell'
    - breakout_index: index of breakout candle (optional, helps narrow search)
    - retest_index: index of retest candle (optional)
    - force_sweep: if True, always return a dummy sweep (for testing)
    - debug: if True, print detailed reasoning

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

    if breakout_index is None:
        if debug:
            print("  [SWEEP] No breakout_index provided → abort")
        return None

    # Define search window: from breakout_index to end of data
    start_idx = breakout_index
    end_idx = len(candles) - 1

    if end_idx - start_idx < 2:
        if debug:
            print(f"  [SWEEP] Not enough candles after breakout (start={start_idx}, end={end_idx})")
        return None

    # Find swings in the entire dataset (or a reasonable lookback)
    swings = find_swings(candles, left=5, right=5)
    swing_highs = [s for s in swings if s['type'] == 'high']
    swing_lows  = [s for s in swings if s['type'] == 'low']

    if direction == 'buy':
        # Buy sweep: price dips below a prior swing low, then closes above it
        # We look for any swing low before breakout_index
        relevant_swings = [s for s in swing_lows if s['index'] < breakout_index]
        if not relevant_swings:
            if debug:
                print("  [SWEEP] No prior swing lows found")
            return None

        # Use the most recent swing low before breakout
        target_swing = max(relevant_swings, key=lambda x: x['index'])
        swing_level = target_swing['price']
        swing_idx = target_swing['index']

        if debug:
            print(f"  [SWEEP] Buy sweep check: looking for dip below swing low {swing_level:.5f} at index {swing_idx}")

        # Scan from breakout_index onward for a candle that dips below swing low
        for i in range(start_idx, end_idx + 1):
            candle_low = candles[i]['low']
            if candle_low < swing_level:
                # Found a dip below swing low. Now check for recovery: a subsequent candle closes above swing level
                for j in range(i + 1, end_idx + 1):
                    if candles[j]['close'] > swing_level:
                        sweep_price = candle_low
                        sweep_index = i
                        if debug:
                            print(f"  [SWEEP] ✅ BUY SWEEP DETECTED: dip at {sweep_price:.5f} (idx {i}), recovery at close {candles[j]['close']:.5f} (idx {j})")
                        return {
                            'index': sweep_index,
                            'price': sweep_price,
                            'swing_index': swing_idx,
                            'recovery_index': j,
                            'forced': False
                        }
                # If we got here, dip occurred but no recovery yet (maybe later? we keep scanning)
        if debug:
            print("  [SWEEP] ❌ No valid buy sweep found (either no dip below swing low or no recovery)")

    else:  # direction == 'sell'
        # Sell sweep: price spikes above a prior swing high, then closes below it
        relevant_swings = [s for s in swing_highs if s['index'] < breakout_index]
        if not relevant_swings:
            if debug:
                print("  [SWEEP] No prior swing highs found")
            return None

        target_swing = max(relevant_swings, key=lambda x: x['index'])
        swing_level = target_swing['price']
        swing_idx = target_swing['index']

        if debug:
            print(f"  [SWEEP] Sell sweep check: looking for spike above swing high {swing_level:.5f} at index {swing_idx}")

        for i in range(start_idx, end_idx + 1):
            candle_high = candles[i]['high']
            if candle_high > swing_level:
                for j in range(i + 1, end_idx + 1):
                    if candles[j]['close'] < swing_level:
                        sweep_price = candle_high
                        sweep_index = i
                        if debug:
                            print(f"  [SWEEP] ✅ SELL SWEEP DETECTED: spike at {sweep_price:.5f} (idx {i}), recovery close {candles[j]['close']:.5f} (idx {j})")
                        return {
                            'index': sweep_index,
                            'price': sweep_price,
                            'swing_index': swing_idx,
                            'recovery_index': j,
                            'forced': False
                        }
        if debug:
            print("  [SWEEP] ❌ No valid sell sweep found (either no spike above swing high or no recovery)")

    return None
