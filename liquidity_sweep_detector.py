"""
Liquidity Sweep Detector (Refined)
Detects liquidity grabs with adaptive sensitivity.
Mode 'adaptive': uses recent low/high since breakout as target.
Mode 'strict': uses prior swing low/high (original logic).
"""

from swing_detector import find_swing_lows, find_swing_highs

def detect_liquidity_sweep(candles, direction, breakout=None, retest=None, lookback=20,
                           debug=False, force_sweep=False, sweep_mode='adaptive'):
    """
    Detect a liquidity sweep.

    Parameters:
    - candles: list of candle dicts (must include 'high','low','close')
    - direction: 'buy' or 'sell'
    - breakout: dict from detect_breakout (contains 'break_index', 'level')
    - retest: dict from detect_retest (optional, contains 'index')
    - lookback: number of candles for swing detection (used in strict mode)
    - debug: if True, print detailed reasoning
    - force_sweep: if True, always return a dummy sweep
    - sweep_mode: 'strict' (original) or 'adaptive' (more sensitive, default)

    Returns:
    - dict with sweep details or None
    """
    if force_sweep:
        if debug:
            print("  [SWEEP] force_sweep=True → returning dummy sweep")
        dummy_price = candles[-1]['low'] if direction == 'buy' else candles[-1]['high']
        return {
            'index': len(candles) - 1,
            'price': dummy_price,
            'level': dummy_price,
            'swing_index': 0,
            'forced': True
        }

    if breakout is None:
        if debug:
            print("  [SWEEP] No breakout provided → abort")
        return None

    breakout_index = breakout.get('break_index')
    if breakout_index is None:
        if debug:
            print("  [SWEEP] Breakout dict missing 'break_index' key")
        return None

    start_idx = breakout_index
    end_idx = len(candles) - 1

    if end_idx - start_idx < 2:
        if debug:
            print(f"  [SWEEP] Not enough candles after breakout (start={start_idx}, end={end_idx})")
        return None

    # ---- Determine Target Level ----
    if sweep_mode == 'adaptive':
        # Use the lowest low (buy) / highest high (sell) since breakout
        if direction == 'buy':
            recent_lows = [candles[i]['low'] for i in range(start_idx, end_idx + 1)]
            target_level = min(recent_lows)
            target_desc = f"lowest low since breakout = {target_level:.5f}"
        else:
            recent_highs = [candles[i]['high'] for i in range(start_idx, end_idx + 1)]
            target_level = max(recent_highs)
            target_desc = f"highest high since breakout = {target_level:.5f}"
        swing_idx = None
        if debug:
            print(f"  [SWEEP] Adaptive mode: {target_desc}")
    else:  # strict mode (original)
        if direction == 'buy':
            swings = find_swing_lows(candles, left=2, right=2)
            if debug:
                print(f"  [SWEEP] Found {len(swings)} swing lows")
            prior_swings = [s for s in swings if s['index'] < breakout_index]
            if not prior_swings:
                if debug:
                    print("  [SWEEP] No prior swing lows found before breakout")
                return None
            target_swing = max(prior_swings, key=lambda x: x['index'])
            target_level = target_swing['level']
            swing_idx = target_swing['index']
            if debug:
                print(f"  [SWEEP] Strict mode: target swing low {target_level:.5f} at index {swing_idx}")
        else:
            swings = find_swing_highs(candles, left=2, right=2)
            if debug:
                print(f"  [SWEEP] Found {len(swings)} swing highs")
            prior_swings = [s for s in swings if s['index'] < breakout_index]
            if not prior_swings:
                if debug:
                    print("  [SWEEP] No prior swing highs found before breakout")
                return None
            target_swing = max(prior_swings, key=lambda x: x['index'])
            target_level = target_swing['level']
            swing_idx = target_swing['index']
            if debug:
                print(f"  [SWEEP] Strict mode: target swing high {target_level:.5f} at index {swing_idx}")

    # ---- Sweep Detection ----
    if direction == 'buy':
        # Look for a dip below target level, then a recovery close above that same target level
        # OR a candle that wicks below and closes above its own low (wick sweep)
        for i in range(start_idx, end_idx + 1):
            candle_low = candles[i]['low']
            if candle_low < target_level:
                # Check for recovery in subsequent candles
                for j in range(i + 1, end_idx + 1):
                    if candles[j]['close'] > target_level:
                        if debug:
                            print(f"  [SWEEP] ✅ BUY SWEEP DETECTED: dip at {candle_low:.5f} (idx {i}), recovery close {candles[j]['close']:.5f} (idx {j})")
                        return {
                            'index': i,
                            'price': candle_low,
                            'level': candle_low,
                            'swing_index': swing_idx,
                            'forced': False,
                            'mode': sweep_mode
                        }
                # Also check if the same candle closed above its own low (wick sweep)
                if candles[i]['close'] > candle_low:
                    if debug:
                        print(f"  [SWEEP] ✅ BUY WICK SWEEP DETECTED: candle {i} wicked to {candle_low:.5f} and closed at {candles[i]['close']:.5f}")
                    return {
                        'index': i,
                        'price': candle_low,
                        'level': candle_low,
                        'swing_index': swing_idx,
                        'forced': False,
                        'mode': sweep_mode
                    }
        if debug:
            print(f"  [SWEEP] ❌ No valid buy sweep (no dip below {target_level:.5f} with recovery)")

    else:  # sell
        for i in range(start_idx, end_idx + 1):
            candle_high = candles[i]['high']
            if candle_high > target_level:
                for j in range(i + 1, end_idx + 1):
                    if candles[j]['close'] < target_level:
                        if debug:
                            print(f"  [SWEEP] ✅ SELL SWEEP DETECTED: spike at {candle_high:.5f} (idx {i}), recovery close {candles[j]['close']:.5f} (idx {j})")
                        return {
                            'index': i,
                            'price': candle_high,
                            'level': candle_high,
                            'swing_index': swing_idx,
                            'forced': False,
                            'mode': sweep_mode
                        }
                if candles[i]['close'] < candle_high:
                    if debug:
                        print(f"  [SWEEP] ✅ SELL WICK SWEEP DETECTED: candle {i} wicked to {candle_high:.5f} and closed at {candles[i]['close']:.5f}")
                    return {
                        'index': i,
                        'price': candle_high,
                        'level': candle_high,
                        'swing_index': swing_idx,
                        'forced': False,
                        'mode': sweep_mode
                    }
        if debug:
            print(f"  [SWEEP] ❌ No valid sell sweep (no spike above {target_level:.5f} with recovery)")

    return None
