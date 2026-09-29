"""
BOS Pipeline — Unified Entry Generator

Combines:
  - Regime state (bos_regime)
  - 5M entry trigger (breakout → retest → rejection → sweep → RR)

Strict mode:
  Only fires signals aligned with the regime's trade_direction.
  No counter-trend signals.
"""

from bos_regime import get_regime
from breakout_detector import detect_breakout
from retest_detector import detect_retest
from rejection_detector import detect_rejection
from liquidity_sweep_detector import detect_liquidity_sweep
from rr_calculator import calculate_rr


MIN_RR = 1.5


def generate_signal(pair, candles_5m, candles_1h, candles_4h, debug=False):
    """
    Returns signal dict or None.
    """
    if len(candles_5m) < 30 or len(candles_1h) < 60 or len(candles_4h) < 40:
        if debug:
            print(f"  [BOS] insufficient candles")
        return None

    # ─── Step 1: Regime ───
    regime = get_regime(candles_4h, candles_1h, debug=debug)
    direction = regime['trade_direction']

    if direction is None:
        if debug:
            print(f"  [BOS] no trade — regime={regime['regime']}")
        return None

    if debug:
        print(f"  [BOS] regime={regime['regime']} → {direction.upper()}")

    # ─── Step 2: 5M breakout ───
    breakout = detect_breakout(
        candles_5m, direction,
        breakout_window=10,
        min_bars_after_swing=3,
        debug=False,
        force_breakout=False,
    )
    if not breakout:
        if debug:
            print(f"  [BOS] no 5M breakout")
        return None

    # ─── Step 3: Retest ───
    retest = detect_retest(
        candles_5m, breakout, direction,
        tolerance_ratio=0.0003,
        max_retest_bars=10,
        debug=False,
    )
    if not retest:
        if debug:
            print(f"  [BOS] no retest")
        return None

    # ─── Step 4: Rejection ───
    rejection = detect_rejection(
        candles_5m, direction,
        retest=retest, breakout=breakout,
        debug=False,
    )
    if not rejection:
        if debug:
            print(f"  [BOS] no rejection")
        return None

    # ─── Step 5: Liquidity sweep ───
    sweep = detect_liquidity_sweep(
        candles_5m, direction,
        breakout=breakout, retest=retest,
        lookback=20, debug=False,
        force_sweep=False,
    )
    if not sweep:
        if debug:
            print(f"  [BOS] no sweep")
        return None

    # ─── Step 6: RR ───
    trade = calculate_rr(
        candles_5m, direction, rejection, sweep,
        min_rr=MIN_RR, debug=False,
    )
    if not trade:
        if debug:
            print(f"  [BOS] RR below {MIN_RR}")
        return None

    # ─── Step 7: Signal ───
    signal = {
        'pair': pair,
        'direction': direction,
        'entry': trade['entry'],
        'sl': trade['sl'],
        'tp': trade['tp'],
        'rr': trade['rr'],
        'regime': regime['regime'],
        'structure_4h': regime['structure_4h'].get('state'),
        'structure_1h': regime['structure_1h'].get('state'),
        'sweep_mode': sweep.get('mode', 'unknown'),
    }

    if debug:
        print(f"  [BOS] ✅ SIGNAL: {direction.upper()} {pair} "
              f"entry={signal['entry']:.5f} SL={signal['sl']:.5f} "
              f"TP={signal['tp']:.5f} RR={signal['rr']:.2f}")

    return signal
