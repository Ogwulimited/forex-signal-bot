from market_data import fetch_candles
from breakout_detector import detect_breakout
from retest_detector import detect_retest
from rejection_detector import detect_rejection
from liquidity_sweep_detector import detect_liquidity_sweep
from chop_filter import is_choppy
from rr_calculator import calculate_rr
from trade_logger import log_trade
from confidence import get_signal_confidence

def generate_signal(bias_data, debug=False, ignore_chop=False, force_breakout=False, force_sweep=False):
    pair = bias_data['pair']
    if not bias_data.get('aligned', False):
        return None
    if bias_data['bias_4h'] == 'bullish':
        direction = 'buy'
    elif bias_data['bias_4h'] == 'bearish':
        direction = 'sell'
    else:
        return None

    # Session filter – only London & NY
    from datetime import datetime
    hour = datetime.utcnow().hour
    if not (7 <= hour < 20):
        if debug: print("Session filter: outside London/NY hours")
        return None

    candles = fetch_candles(pair, interval='5min', outputsize=100)
    if not candles or len(candles) < 30:
        return None

    # Chop filter re‑enabled
    if not ignore_chop:
        if is_choppy(candles, lookback=20, min_range_ratio=0.0005):
            return None

    breakout = detect_breakout(candles, direction, breakout_window=5, min_bars_after_swing=3, debug=debug, force_breakout=force_breakout)
    if not breakout:
        return None

    retest = detect_retest(candles, breakout, direction, tolerance_ratio=0.0003, max_retest_bars=10, debug=debug)
    if not retest:
        return None

    rejection = detect_rejection(candles, direction, retest=retest, breakout=breakout, debug=debug)
    if not rejection:
        return None

    sweep = detect_liquidity_sweep(candles, direction, breakout=breakout, retest=retest, lookback=20, debug=debug, force_sweep=force_sweep)
    if not sweep:
        return None

    trade = calculate_rr(candles, direction, rejection, sweep, min_rr=2.0, debug=debug)
    if not trade:
        return None

    signal = {
        'pair': pair,
        'direction': direction,
        'entry': trade['entry'],
        'sl': trade['sl'],
        'tp': trade['tp'],
        'timeframe': '5M',
        'rr': trade['rr']
    }

    # Confidence (optional but useful once you have history)
    confidence = get_signal_confidence(signal, bias_data, breakout, rejection, sweep)
    if confidence:
        signal['confidence'] = confidence

    log_trade(signal, bias_data, breakout, rejection, sweep, direction)
    return signal
