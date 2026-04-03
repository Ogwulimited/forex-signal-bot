import traceback
from mtf_bias_engine import get_mtf_bias
from signal_dispatcher import generate_signal
from signal_formatter import format_signal
from telegram_sender import send_telegram_message

TEST_PAIR = "AUDUSD"  # change this as needed

def run_test():
    print("One-pair 5M entry engine test started...", flush=True)

    try:
        print(f"Checking {TEST_PAIR}...", flush=True)

        bias = get_mtf_bias(TEST_PAIR)
        print(f"Bias for {TEST_PAIR}: {bias}", flush=True)

        if not bias.get("aligned"):
            print(f"{TEST_PAIR} is not HTF aligned. Skipping 5M test.", flush=True)
            return

        signal = generate_signal(bias, debug=True, ignore_chop=True)
        print(f"Generated signal for {TEST_PAIR}: {signal}", flush=True)

        if signal:
            message = format_signal(signal)
            send_telegram_message(message)
            print("Test signal sent to Telegram.", flush=True)
        else:
            print("No valid 5M entry setup found.", flush=True)

    except Exception as e:
        print(f"Error during one-pair test: {e}", flush=True)
        traceback.print_exc()

    print("One-pair 5M entry engine test completed.", flush=True)

if __name__ == "__main__":
    run_test()
