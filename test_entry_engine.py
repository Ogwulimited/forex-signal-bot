"""
Simple test harness for 5M entry signals.
Uses the existing generate_signal function.
"""
from mtf_bias_engine import get_mtf_bias
from signal_dispatcher import generate_signal

PAIR = "EURUSD"

def main():
    print(f"\n=== TEST ENTRY SIGNAL FOR {PAIR} ===\n")

    # Get HTF bias
    bias_data = get_mtf_bias(PAIR)
    if not bias_data:
        print("❌ Failed to get MTF bias.")
        return

    print(f"4H bias: {bias_data['bias_4h']} (strength={bias_data['strength_4h']})")
    print(f"1H bias: {bias_data['bias_1h']} (strength={bias_data['strength_1h']})")
    print(f"Aligned: {bias_data['aligned']}")

    # Run signal generation with debug ON
    # force_breakout=True so we can test the sweep detector even without a real breakout
    print("\n--- Running generate_signal (force_breakout=True for sweep debug) ---\n")
    signal = generate_signal(
        bias_data=bias_data,
        debug=True,
        ignore_chop=True,
        force_breakout=True,    # <-- Force breakout to reach sweep detector
        force_sweep=False       # <-- We want natural sweep detection
    )

    if signal:
        print("\n✅ SIGNAL GENERATED:")
        print(signal)
    else:
        print("\n❌ No signal generated.")

    print("\n=== TEST COMPLETE ===")

if __name__ == "__main__":
    main()
