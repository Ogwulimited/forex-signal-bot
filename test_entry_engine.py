"""
Standalone Sweep Detector Debugger
Bypasses retest/rejection to focus solely on liquidity sweep logic.
"""
from market_data import fetch_candles
from mtf_bias_engine import get_mtf_bias
from liquidity_sweep_detector import detect_liquidity_sweep

PAIR = "EURUSD"

def main():
    print(f"\n=== SWEEP DETECTOR DEBUG ({PAIR}) ===\n")

    # Fetch 5M candles
    candles = fetch_candles(PAIR, interval="5min", outputsize=100)
    if not candles:
        print("❌ Failed to fetch candles.")
        return
    print(f"✅ Fetched {len(candles)} candles")

    # Get direction from MTF bias
    bias_data = get_mtf_bias(PAIR)
    if not bias_data:
        print("❌ Failed to get MTF bias.")
        return

    if bias_data['bias_4h'] == 'bullish':
        direction = 'buy'
    elif bias_data['bias_4h'] == 'bearish':
        direction = 'sell'
    else:
        print(f"Neutral bias, defaulting to 'buy' for testing.")
        direction = 'buy'

    print(f"Direction: {direction}")

    # Simulate a breakout at a realistic index (not the very last candle)
    # Choose index 10 candles from the end to leave room for potential sweep/recovery
    breakout_index = max(0, len(candles) - 11)
    simulated_breakout = {
        'break_index': breakout_index,
        'level': candles[breakout_index]['close'],  # rough level
        'forced': True
    }

    print(f"\n--- Simulated breakout at index {breakout_index} ---")

    # Run sweep detector with force_sweep=False, debug=True
    print("\n--- Running sweep detector (force_sweep=False) ---\n")
    sweep = detect_liquidity_sweep(
        candles=candles,
        direction=direction,
        breakout=simulated_breakout,
        retest=None,           # Not needed for sweep detection
        lookback=20,
        debug=True,
        force_sweep=False
    )

    if sweep:
        print("\n✅ SWEEP DETECTED:")
        for k, v in sweep.items():
            print(f"  {k}: {v}")
    else:
        print("\n❌ No sweep detected.")

    print("\n=== DEBUG COMPLETE ===")

if __name__ == "__main__":
    main()
