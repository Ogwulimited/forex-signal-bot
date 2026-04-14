"""
Improved liquidity sweep detector – more permissive and detailed.
"""

from swing_detector import find_swing_highs, find_swing_lows

def detect_liquidity_sweep(candles, direction, breakout=None, retest=None, lookback=20, debug=False, force_sweep=False):
    """
    Detect liquidity sweep with more flexibility.
    """
    if len(candles) < lookback:
        if debug:
            print("Liquidity sweep: insufficient candles")
        return None
    
    # Reference index: use retest index if available, else breakout, else last candle
    reference_index = len(candles) - 1
    if retest and retest.get('retest_index') is not None:
        reference_index = retest['retest_index']
    elif breakout and breakout.get('break_index') is not None:
        reference_index = breakout['break_index']
    
    if debug:
        print(f"Liquidity sweep: looking for sweep before index {reference_index}")
    
    relevant_candles = candles[:reference_index + 1]
    swing_highs = find_swing_highs(relevant_candles, left=2, right=2)
    swing_lows = find_swing_lows(relevant_candles, left=2, right=2)
    
    min_swing_index = max(0, reference_index - lookback)
    
    if direction == 'buy':
        # Get all recent swing lows
        recent_swing_lows = [s for s in swing_lows if min_swing_index <= s['index'] < reference_index]
        if not recent_swing_lows:
            if debug:
                print("Liquidity sweep: no recent swing lows found")
        else:
            if debug:
                print(f"Liquidity sweep: found {len(recent_swing_lows)} recent swing lows")
            # Check each swing low (from most recent to oldest) for a sweep
            for swing in sorted(recent_swing_lows, key=lambda x: x['index'], reverse=True):
                sweep_level = swing['level']
                if debug:
                    print(f"  Checking swing low at index {swing['index']} level={sweep_level}")
                # Look for a candle after the swing low that sweeps below and recovers
                for i in range(swing['index'] + 1, reference_index):
                    candle = candles[i]
                    if candle['low'] < sweep_level:
                        # Sweep occurred – now check if price recovered above sweep_level by reference_index
                        # We'll consider any candle after the sweep that closes above sweep_level (or the close at reference_index)
                        recovered = False
                        for j in range(i, reference_index + 1):
                            if candles[j]['close'] > sweep_level:
                                recovered = True
                                break
                        if recovered:
                            if debug:
                                print(f"    ✅ Sweep detected at index {i}, low={candle['low']}, recovered by index {j if recovered else '?'}")
                            return {
                                'level': sweep_level,
                                'sweep_index': i,
                                'type': 'buy_sweep',
                                'candle': candle,
                                'forced': False
                            }
                        else:
                            if debug:
                                print(f"    Sweep at index {i} but no recovery")
                if debug:
                    print(f"  No valid sweep for this swing low")
    
    else:  # sell
        recent_swing_highs = [s for s in swing_highs if min_swing_index <= s['index'] < reference_index]
        if not recent_swing_highs:
            if debug:
                print("Liquidity sweep: no recent swing highs found")
        else:
            if debug:
                print(f"Liquidity sweep: found {len(recent_swing_highs)} recent swing highs")
            for swing in sorted(recent_swing_highs, key=lambda x: x['index'], reverse=True):
                sweep_level = swing['level']
                if debug:
                    print(f"  Checking swing high at index {swing['index']} level={sweep_level}")
                for i in range(swing['index'] + 1, reference_index):
                    candle = candles[i]
                    if candle['high'] > sweep_level:
                        recovered = False
                        for j in range(i, reference_index + 1):
                            if candles[j]['close'] < sweep_level:
                                recovered = True
                                break
                        if recovered:
                            if debug:
                                print(f"    ✅ Sweep detected at index {i}, high={candle['high']}, recovered by index {j}")
                            return {
                                'level': sweep_level,
                                'sweep_index': i,
                                'type': 'sell_sweep',
                                'candle': candle,
                                'forced': False
                            }
                        else:
                            if debug:
                                print(f"    Sweep at index {i} but no recovery")
                if debug:
                    print(f"  No valid sweep for this swing high")
    
    # No real sweep – force if requested
    if force_sweep:
        if debug:
            print(f"Liquidity sweep: FORCING simulated sweep for {direction}")
        fake_index = max(0, reference_index - 1)
        fake_candle = candles[fake_index]
        if direction == 'buy':
            fake_level = fake_candle['low'] * 0.999
            return {
                'level': fake_level,
                'sweep_index': fake_index,
                'type': 'buy_sweep',
                'candle': fake_candle,
                'forced': True
            }
        else:
            fake_level = fake_candle['high'] * 1.001
            return {
                'level': fake_level,
                'sweep_index': fake_index,
                'type': 'sell_sweep',
                'candle': fake_candle,
                'forced': True
            }
    
    return None
