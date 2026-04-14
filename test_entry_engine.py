"""
Standalone Sweep Detector Debug Script
Forces breakout/retest to isolate liquidity sweep logic.
"""
from market_data import fetch_candles
from mtf_bias_engine import get_mtf_bias
from liquidity_sweep_detector import detect_liquidity_sweep

PAIR = "EURUSD"
TIMEFRAME = "5min"
OUTPUT_SIZE = 100

def main():
    print(f"\n=== SWEEP DETECTOR DEBUG ({PAIR}) ===\n")

    # Fetch 5M candles
    candles = fetch_candles(PAIR, TIMEFRAME, OUTPUT_SIZE)
    if not candles:
        print("❌ Failed to fetch candles.")
        return
    print(f"✅ Fetched {len(candles)} candles")

    # Get bias to determine direction
    bias_data = get_mtf_bias(PAIR)
    if not bias_data or not bias_data.get('aligned'):
        print("❌ HTF not aligned or bias unavailable.")
        return

    direction = 'buy' if bias_data['bias_4h'] == 'bullish' else 'sell'
    print(f"Direction: {direction}")

    # Force a breakout at a specific index (simulate one)
    # Use an index around 2/3 into the data so there's room for sweep/recovery
    breakout_index = int(len(candles) * 0.7)
    forced_breakout = {
        'break_index': breakout_index,
        'level': candles[breakout_index]['close'],
        'forced': True
    }
    print(f"\n[FORCED] Breakout simulated at index {breakout_index}, level {forced_breakout['level']:.5f}")

    # Simulate a retest (not actually used by sweep detector but passed for compatibility)
    forced_retest = {'index': breakout_index + 2}

    # Run sweep detector with debug ON, force_sweep OFF
    print("\n--- Running sweep detector (force_sweep=False) ---\n")
    sweep = detect_liquidity_sweep(
        candles=candles,
        direction=direction,
        breakout=forced_breakout,
        retest=forced_retest,
        lookback=20,
        debug=True,
        force_sweep=False
    )

    if sweep:
        print("\n✅ SWEEP DETECTED:")
        print(sweep)
    else:
        print("\n❌ No sweep detected.")

    print("\n=== DEBUG COMPLETE ===")

if __name__ == "__main__":
    main()
