"""
Test entry signal using generate_signal from signal_dispatcher.
Runs full 5M pipeline with debug=True, force flags OFF.
"""
from mtf_bias_engine import get_mtf_bias
from signal_dispatcher import generate_signal

PAIR = "EURUSD"

def main():
    print(f"\n=== TEST ENTRY SIGNAL FOR {PAIR} ===\n")

    # 1. Get HTF bias
    bias_data = get_mtf_bias(PAIR)
    if not bias_data:
        print("❌ Failed to get MTF bias.")
        return

    print(f"4H bias: {bias_data['bias_4h']} (strength={bias_data['strength_4h']})")
    print(f"1H bias: {bias_data['bias_1h']} (strength={bias_data['strength_1h']})")
    print(f"Aligned: {bias_data['aligned']}")

    # 2. Run signal generation
    print("\n--- Running generate_signal (debug ON, force flags OFF) ---\n")
    signal = generate_signal(
        bias_data=bias_data,
        debug=True,
        ignore_chop=True,          # Keep chop filter bypassed for now
        force_breakout=False,
        force_sweep=False          # Natural sweep detection
    )

    if signal:
        print("\n✅ SIGNAL GENERATED:")
        for k, v in signal.items():
            print(f"  {k}: {v}")
    else:
        print("\n❌ No signal generated.")

    print("\n=== TEST COMPLETE ===")

if __name__ == "__main__":
    main()
