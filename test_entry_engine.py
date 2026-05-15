"""
Diagnostic Script – Pipeline Test with Breakout Debug
Tests EURUSD and GBPUSD only (safe from rate limits).
"""
import time
from market_data import fetch_candles
from mtf_bias_engine import get_mtf_bias
from breakout_detector import detect_breakout
from retest_detector import detect_retest
from rejection_detector import detect_rejection
from liquidity_sweep_detector import detect_liquidity_sweep
from rr_calculator import calculate_rr
from chop_filter import is_choppy

PAIRS = ["EURUSD", "GBPUSD"]
DELAY_BETWEEN = 30

def main():
    print("=" * 60)
    print("DIAGNOSTIC PIPELINE TEST – EURUSD & GBPUSD")
    print("=" * 60)

    results = []

    for pair in PAIRS:
        print(f"\n--- {pair} ---")
        result = {
            "pair": pair,
            "bias": None,
            "aligned": False,
            "direction": None,
            "breakout": False,
            "retest": False,
            "rejection": False,
            "sweep": False,
            "rr": False,
            "signal": False,
            "error": None
        }

        try:
            bias_data = get_mtf_bias(pair)
            if not bias_data:
                result["error"] = "No bias data"
                results.append(result)
                continue
            result["bias"] = bias_data['bias_4h']
            result["aligned"] = bias_data.get('aligned', False)
            if not result["aligned"]:
                result["error"] = "HTF not aligned"
                results.append(result)
                print(f"  Bias: {bias_data['bias_4h']}/{bias_data['bias_1h']} – not aligned")
                continue
            direction = 'buy' if bias_data['bias_4h'] == 'bullish' else 'sell'
            result["direction"] = direction
            print(f"  Bias: {bias_data['bias_4h']} | Aligned ✅ | Direction: {direction}")

            candles = fetch_candles(pair, interval='5min', outputsize=100)
            if not candles or len(candles) < 30:
                result["error"] = "Insufficient 5M candles"
                results.append(result)
                continue

            if is_choppy(candles, lookback=20, min_range_ratio=0.0005):
                result["error"] = "Choppy market"
                results.append(result)
                print("  Market choppy – skipped")
                continue

            print("  [DEBUG] Breakout search:")
            breakout = detect_breakout(candles, direction, breakout_window=10, min_bars_after_swing=3, debug=True, force_breakout=False)
            if breakout:
                result["breakout"] = True
                print(f"  Breakout ✅ (idx {breakout.get('break_index')})")
            else:
                result["error"] = "No breakout"
                results.append(result)
                continue

            retest = detect_retest(candles, breakout, direction, tolerance_ratio=0.0003, max_retest_bars=10, debug=False)
            if retest:
                result["retest"] = True
                print(f"  Retest ✅ (idx {retest.get('index')})")
            else:
                result["error"] = "No retest"
                results.append(result)
                continue

            rejection = detect_rejection(candles, direction, retest=retest, breakout=breakout, debug=False)
            if rejection:
                result["rejection"] = True
                print(f"  Rejection ✅ (idx {rejection.get('index')})")
            else:
                result["error"] = "No rejection"
                results.append(result)
                continue

            sweep = detect_liquidity_sweep(candles, direction, breakout=breakout, retest=retest, lookback=20, debug=False, force_sweep=False, sweep_mode='adaptive')
            if sweep:
                result["sweep"] = True
                print(f"  Sweep ✅ (idx {sweep.get('index')})")
            else:
                result["error"] = "No sweep"
                results.append(result)
                continue

            trade = calculate_rr(candles, direction, rejection, sweep, min_rr=1.5, debug=False)
            if trade and trade.get('rr', 0) >= 1.5:
                result["rr"] = True
                result["signal"] = True
                print(f"  RR ✅ ({trade['rr']:.2f}) – SIGNAL GENERATED")
            else:
                result["error"] = f"RR insufficient ({trade.get('rr', 0) if trade else 0})"
                results.append(result)
                continue

            results.append(result)

        except Exception as e:
            result["error"] = str(e)[:100]
            results.append(result)
            print(f"  ❌ ERROR: {e}")

        if pair != PAIRS[-1]:
            time.sleep(DELAY_BETWEEN)

    # ---- SUMMARY (fixed formatting) ----
    print("\n" + "=" * 60)
    print("SUMMARY TABLE")
    print("=" * 60)
    header = f"{'Pair':<10} {'Bias':<10} {'B/O':<5} {'Retest':<7} {'Rej':<5} {'Sweep':<6} {'RR':<5} {'SIGNAL':<7} {'Error'}"
    print(header)
    print("-" * 60)
    for r in results:
        bias_str = r.get('bias') or '?'
        print(f"{r['pair']:<10} {bias_str:<10} {'✅' if r['breakout'] else '❌':<5} "
              f"{'✅' if r['retest'] else '❌':<7} {'✅' if r['rejection'] else '❌':<5} "
              f"{'✅' if r['sweep'] else '❌':<6} {'✅' if r['rr'] else '❌':<5} "
              f"{'✅' if r['signal'] else '❌':<7} {r.get('error',''):<30}")
    print("=" * 60)
    signals = [r for r in results if r['signal']]
    print(f"Total pairs: {len(PAIRS)} | Signals generated: {len(signals)}")
    if not signals:
        print("No signals in this scan. Common blockers are:")
        print(" - HTF misalignment")
        print(" - No breakout / no retest")
        print(" - Sweep missing")
        print(" - RR below 1.5")
    print("\nDiagnostic complete.")

if __name__ == "__main__":
    main()
