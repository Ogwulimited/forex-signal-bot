"""
Diagnostic Script – All Pairs Pipeline Test
Tests every stage of the 5M entry pipeline and prints a summary.
"""
import time
import sys
from market_data import fetch_candles
from mtf_bias_engine import get_mtf_bias
from breakout_detector import detect_breakout
from retest_detector import detect_retest
from rejection_detector import detect_rejection
from liquidity_sweep_detector import detect_liquidity_sweep
from rr_calculator import calculate_rr
from chop_filter import is_choppy

PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]
RESULTS = []

def main():
    print("=" * 60)
    print("DIAGNOSTIC PIPELINE TEST – ALL PAIRS")
    print("=" * 60)

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
            # 1. Bias
            bias_data = get_mtf_bias(pair)
            if not bias_data:
                result["error"] = "No bias data"
                RESULTS.append(result)
                continue
            result["bias"] = bias_data['bias_4h']
            result["aligned"] = bias_data.get('aligned', False)
            if not result["aligned"]:
                result["error"] = "HTF not aligned"
                RESULTS.append(result)
                print(f"  Bias: {bias_data['bias_4h']}/{bias_data['bias_1h']} – not aligned")
                continue
            direction = 'buy' if bias_data['bias_4h'] == 'bullish' else 'sell'
            result["direction"] = direction
            print(f"  Bias: {bias_data['bias_4h']} | Aligned ✅ | Direction: {direction}")

            # Small delay
            time.sleep(1.5)

            # 2. Fetch 5M candles
            candles = fetch_candles(pair, interval='5min', outputsize=100)
            if not candles or len(candles) < 30:
                result["error"] = "Insufficient 5M candles"
                RESULTS.append(result)
                continue

            # 3. Chop filter (optional)
            if is_choppy(candles, lookback=20, min_range_ratio=0.0005):
                result["error"] = "Choppy market"
                RESULTS.append(result)
                print("  Market choppy – skipped")
                continue

            # 4. Breakout
            breakout = detect_breakout(candles, direction, breakout_window=5, min_bars_after_swing=3, debug=False, force_breakout=False)
            if breakout:
                result["breakout"] = True
                print(f"  Breakout ✅ (idx {breakout.get('break_index')})")
            else:
                result["error"] = "No breakout"
                RESULTS.append(result)
                print("  Breakout ❌")
                continue

            # 5. Retest
            retest = detect_retest(candles, breakout, direction, tolerance_ratio=0.0003, max_retest_bars=10, debug=False)
            if retest:
                result["retest"] = True
                print(f"  Retest ✅ (idx {retest.get('index')})")
            else:
                result["error"] = "No retest"
                RESULTS.append(result)
                print("  Retest ❌")
                continue

            # 6. Rejection
            rejection = detect_rejection(candles, direction, retest=retest, breakout=breakout, debug=False)
            if rejection:
                result["rejection"] = True
                print(f"  Rejection ✅ (idx {rejection.get('index')})")
            else:
                result["error"] = "No rejection"
                RESULTS.append(result)
                print("  Rejection ❌")
                continue

            # 7. Sweep (adaptive mode)
            sweep = detect_liquidity_sweep(candles, direction, breakout=breakout, retest=retest, lookback=20, debug=False, force_sweep=False, sweep_mode='adaptive')
            if sweep:
                result["sweep"] = True
                print(f"  Sweep ✅ (idx {sweep.get('index')})")
            else:
                result["error"] = "No sweep"
                RESULTS.append(result)
                print("  Sweep ❌")
                continue

            # 8. RR
            trade = calculate_rr(candles, direction, rejection, sweep, min_rr=1.5, debug=False)
            if trade and trade.get('rr', 0) >= 1.5:
                result["rr"] = True
                result["signal"] = True
                print(f"  RR ✅ ({trade['rr']:.2f}) – SIGNAL GENERATED")
            else:
                result["error"] = f"RR insufficient ({trade.get('rr', 0) if trade else 0})"
                RESULTS.append(result)
                print(f"  RR ❌")
                continue

            RESULTS.append(result)

        except Exception as e:
            result["error"] = str(e)[:100]
            RESULTS.append(result)
            print(f"  ❌ ERROR: {e}")

        # Delay between pairs to respect API limit
        if pair != PAIRS[-1]:
            time.sleep(20)

    # ---- SUMMARY ----
    print("\n" + "=" * 60)
    print("SUMMARY TABLE")
    print("=" * 60)
    print(f"{'Pair':<10} {'Bias':<10} {'B/O':<5} {'Retest':<7} {'Rej':<5} {'Sweep':<6} {'RR':<5} {'SIGNAL':<7} {'Error'}")
    print("-" * 60)
    for r in RESULTS:
        print(f"{r['pair']:<10} {r.get('bias','?'):<10} {'✅' if r['breakout'] else '❌':<5} "
              f"{'✅' if r['retest'] else '❌':<7} {'✅' if r['rejection'] else '❌':<5} "
              f"{'✅' if r['sweep'] else '❌':<6} {'✅' if r['rr'] else '❌':<5} "
              f"{'✅' if r['signal'] else '❌':<7} {r.get('error',''):<30}")
    print("=" * 60)
    signals = [r for r in RESULTS if r['signal']]
    print(f"Total pairs: {len(PAIRS)} | Signals generated: {len(signals)}")
    if not signals:
        print("No signals in this scan. Common blockers are:")
        print(" - HTF misalignment")
        print(" - No breakout / no retest")
        print(" - Sweep missing (check adaptive logs)")
        print(" - RR below 1.5")
    print("\nDiagnostic complete.")

if __name__ == "__main__":
    main()
