"""
Liquidity Sweep Detector – Ultra-Relaxed
- Sell sweep: any upper wick above retest or breakout level, or spike above recent highest high
- Buy sweep: any lower wick below retest or breakout level, or dip below recent lowest low
- No separate recovery required; rejection candle confirms.
"""

from swing_detector import find_swing_lows, find_swing_highs

def detect_liquidity_sweep(candles, direction, breakout=None, retest=None, lookback=20,
                           debug=False, force_sweep=False, sweep_mode='adaptive'):
    """
    Detect a liquidity sweep with lenient conditions.

    Parameters:
    - sweep_mode: 'adaptive' (default, relaxed) or 'strict' (original prior-swing)
    """
    if force_sweep:
        if debug:
            print("  [SWEEP] force_sweep=True → returning dummy sweep")
        dummy = candles[-1]['low'] if direction == 'buy' else candles[-1]['high']
        return {'index': len(candles)-1, 'price': dummy, 'level': dummy, 'swing_index': 0, 'forced': True}

    if breakout is None:
        if debug:
            print("  [SWEEP] No breakout → abort")
        return None

    breakout_index = breakout.get('break_index')
    if breakout_index is None:
        if debug:
            print("  [SWEEP] Breakout missing 'break_index'")
        return None

    end_idx = len(candles) - 1
    if end_idx - breakout_index < 1:
        if debug:
            print("  [SWEEP] Not enough candles after breakout")
        return None

    # Determine reference level
    if sweep_mode == 'strict':
        # Original prior-swing logic
        if direction == 'buy':
            swings = find_swing_lows(candles, left=2, right=2)
            prior = [s for s in swings if s['index'] < breakout_index]
            if not prior:
                if debug: print("  [SWEEP] No prior swing lows")
                return None
            ref = max(prior, key=lambda x: x['index'])
            ref_level = ref['level']
            swing_idx = ref['index']
        else:
            swings = find_swing_highs(candles, left=2, right=2)
            prior = [s for s in swings if s['index'] < breakout_index]
            if not prior:
                if debug: print("  [SWEEP] No prior swing highs")
                return None
            ref = max(prior, key=lambda x: x['index'])
            ref_level = ref['level']
            swing_idx = ref['index']
    else:
        # Adaptive: use retest level if available, else breakout level
        if retest and retest.get('index') is not None:
            idx = retest['index']
            ref_level = candles[idx]['close']  # retest price
            swing_idx = None
            if debug:
                print(f"  [SWEEP] Adaptive: using retest level {ref_level:.5f} at index {idx}")
        else:
            ref_level = breakout.get('level', candles[breakout_index]['close'])
            swing_idx = None
            if debug:
                print(f"  [SWEEP] Adaptive: using breakout level {ref_level:.5f}")

    # Sweep detection (lenient)
    if direction == 'buy':
        # Any candle with low below reference level is a sweep
        for i in range(breakout_index, end_idx + 1):
            if candles[i]['low'] < ref_level:
                price = candles[i]['low']
                if debug:
                    print(f"  [SWEEP] ✅ BUY SWEEP: candle {i} low {price:.5f} < {ref_level:.5f}")
                return {'index': i, 'price': price, 'level': price, 'swing_index': swing_idx, 'forced': False, 'mode': sweep_mode}
        if debug:
            print(f"  [SWEEP] ❌ No buy sweep (no low below {ref_level:.5f})")
    else:  # sell
        for i in range(breakout_index, end_idx + 1):
            if candles[i]['high'] > ref_level:
                price = candles[i]['high']
                if debug:
                    print(f"  [SWEEP] ✅ SELL SWEEP: candle {i} high {price:.5f} > {ref_level:.5f}")
                return {'index': i, 'price': price, 'level': price, 'swing_index': swing_idx, 'forced': False, 'mode': sweep_mode}
        if debug:
            print(f"  [SWEEP] ❌ No sell sweep (no high above {ref_level:.5f})")

    return None
