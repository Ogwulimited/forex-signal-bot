import time
from mtf_bias_engine import get_mtf_bias
from signal_dispatcher import generate_signal
from signal_formatter import format_signal
from telegram_sender import send_telegram_message


CHECK_INTERVAL = 300  # 5 minutes


def run_bot():
    print("Bot started...")

    while True:
        try:
            print("Checking market...")

            # Step 1: Get bias
            bias = get_mtf_bias("EURUSD")

            # Step 2: Generate signal
            signal = generate_signal(bias)

            # Step 3: Only send if valid
            if signal:
                message = format_signal(signal)
                send_telegram_message(message)
                print("Signal sent:", message)
            else:
                print("No trade setup.")

        except Exception as e:
            print("Error:", e)

        # Wait 5 minutes
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    run_bot()
