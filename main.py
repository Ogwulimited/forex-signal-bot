import time
import traceback
from mtf_bias_engine import get_mtf_bias
from signal_generator import generate_signal
from signal_formatter import format_signal
from telegram_sender import send_telegram_message

CHECK_INTERVAL = 300  # seconds = 5 minutes
PAIRS = ["EURUSD"]    # we'll add more later

def run_bot():
    print("Bot started. Waiting for first check...")
    while True:
        try:
            for pair in PAIRS:
                print(f"\n--- Checking {pair} at {time.ctime()} ---")
                bias = get_mtf_bias(pair)
                signal = generate_signal(bias, pair)
                if signal:
                    message = format_signal(signal)
                    send_telegram_message(message)
                    print("Signal sent.")
                else:
                    print("No valid setup.")
        except Exception:
            print("Unhandled error:")
            traceback.print_exc()
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    run_bot()
