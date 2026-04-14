"""
Test Entry Engine - Manual one-pair 5M debug harness
Run with: python test_entry_engine.py
"""
import json
import sys
from market_data import fetch_candles
from signal_dispatcher import check_entry_signal

# Try to import the bias function with the correct name
try:
    from mtf_bias_engine import get_mtf_bias as compute_mtf_bias
except ImportError:
    try:
        from mtf_bias_engine import compute_bias as compute_mtf_bias
    except ImportError:
        # If both fail, import the module and list functions to help debug
        import mtf_bias_engine
        print("Available functions in mtf_bias_engine:", [f for f in dir(mtf_bias_engine) if not f.startswith('_')])
        sys.exit(1)

# Configuration
PAIR = "EURUSD"          # Change to any pair you want to test
TIMEFRAME = "5min"
OUTPUT_SIZE = 200        # Fetch enough candles for swing detection

def main():
    print(f"\n=== TEST ENTRY ENGINE ===\n")
    print(f"Pair: {PAIR}, Timeframe: {TIMEFRAME}, Candles: {OUTPUT_SIZE}")

    # 1. Fetch 5M candles
    candles = fetch_candles(PAIR, TIMEFRAME, OUTPUT_SIZE)
    if not candles:
        print("❌ Failed to fetch candles. Check API key and network.")
        return

    print(f"✅ Fetched {len(candles)} candles")

    # 2. Compute HTF bias (requires 4H and 1H data)
    print("\n--- Computing MTF Bias ---")
    bias_data = compute_mtf_bias(PAIR)
    if not bias_data:
        print("❌ Failed to compute MTF bias (API issue or insufficient data)")
        return

    print(f"4H bias: {bias_data['bias_4h']} (strength={bias_data['strength_4h']}, range_ratio={bias_data['range_ratio_4h']:.4f})")
    print(f"1H bias: {bias_data['bias_1h']} (strength={bias_data['strength_1h']}, range_ratio={bias_data['range_ratio_1h']:.4f})")
    print(f"Aligned: {bias_data['aligned']}")

    # 3. Check entry signal (with force flags OFF)
    print("\n--- Checking Entry Signal ---")
    result = check_entry_signal(
        pair=PAIR,
        candles_5m=candles,
        bias_data=bias_data,
        force_breakout=False,   # Keep false for realistic test
        force_sweep=False,      # Important: we want natural detection
        ignore_chop=True,       # Keep chop filter bypassed for now
        debug=True
    )

    if result:
        print("\n✅ SIGNAL FOUND!")
        print(json.dumps(result, indent=2))
    else:
        print("\n❌ No valid entry signal.")

    print("\n=== TEST COMPLETE ===")

if __name__ == "__main__":
    main()
