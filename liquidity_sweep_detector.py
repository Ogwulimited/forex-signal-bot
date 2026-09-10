"""
Strict Liquidity Sweep – requires actual sweep of prior swing with recovery.
"""

from swing_detector import find_swing_lows, find_swing_highs

def detect_liquidity_sweep(candles, direction, breakout=None, retest=None, lookback=20, debug=False, force_sweep=False):
    if force_sweep:
        dummy = candles[-1]['low'] if direction == 'buy' else candles[-1]['high']
        return {'index': len(candles)-1, 'price': dummy, 'level': dummy, 'swing_index': 0, 'forced': True}

    if breakout is None:
        return None

    breakout_index = breakout.get('break_index')
    if breakout_index is None:
        return None

    end_idx = len(candles) - 1
    if end_idx - breakout_index < 2:
        return None

    if direction == 'buy':
        swings = find_swing_lows(candles, left=2, right=2)
        prior = [s for s in swings if s['index'] < breakout_index]
        if not prior:
            return None
        target = max(prior, key=lambda x: x['index'])
        level = target['level']
        for i in range(breakout_index, end_idx + 1):
            if candles[i]['low'] < level:
                for j in range(i+1, end_idx+1):
                    if candles[j]['close'] > level:
                        return {'index': i, 'price': candles[i]['low'], 'level': candles[i]['low'], 'swing_index': target['index'], 'forced': False}
    else:
        swings = find_swing_highs(candles, left=2, right=2)
        prior = [s for s in swings if s['index'] < breakout_index]
        if not prior:
            return None
        target = max(prior, key=lambda x: x['index'])
        level = target['level']
        for i in range(breakout_index, end_idx + 1):
            if candles[i]['high'] > level:
                for j in range(i+1, end_idx+1):
                    if candles[j]['close'] < level:
                        return {'index': i, 'price': candles[i]['high'], 'level': candles[i]['high'], 'swing_index': target['index'], 'forced': False}
    return None
