import traceback
from mtf_bias_engine import get_mtf_bias
from signal_dispatcher import generate_signal
from signal_formatter import format_signal
from telegram_sender import send_telegram_message
from signal_state import is_duplicate_signal

PAIRS = [
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "AUDUSD",
    "USDCAD",
    "USDCHF",
    "NZDUSD",
    "EURJPY",
    "GBPJPY",
    "EURGBP"
]

def run_once():
    print("Bot scan started...", flush=True)

    for pair in PAIRS:
        try:
            print(f"Checking {pair}...", flush=True)

            bias = get_mtf_bias(pair)
            print(f"Bias for {pair}: {bias}", flush=True)

            if not bias.get("aligned"):
                print(f"Skipping {pair} - HTF not aligned.", flush=True)
                continue

            signal = generate_signal(bias)
            print(f"Signal for {pair}: {signal}", flush=True)

            if signal:
                if not is_duplicate_signal(signal):
                    message = format_signal(signal)
                    send_telegram_message(message)
                    print(f"Signal sent for {pair}", flush=True)
                else:
                    print(f"Duplicate signal blocked for {pair}", flush=True)
            else:
                print(f"No valid setup for {pair}", flush=True)

        except Exception as e:
            print(f"Error on {pair}: {e}", flush=True)
            traceback.print_exc()

    print("Bot scan completed.", flush=True)

if __name__ == "__main__":
    run_once()
