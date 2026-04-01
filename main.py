import traceback
from mtf_bias_engine import get_mtf_bias
from watchlist_formatter import format_watchlist_alert
from watchlist_state import should_send_watchlist_alert
from telegram_sender import send_telegram_message

PAIRS = [
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "AUDUSD"
]

def run_once():
    print("Bot scan started...", flush=True)

    for pair in PAIRS:
        try:
            print(f"Checking {pair}...", flush=True)

            bias = get_mtf_bias(pair)
            print(f"Bias for {pair}: {bias}", flush=True)

            if bias.get("aligned"):
                print(f"{pair} is aligned for potential setup.", flush=True)

                direction = bias["bias_4h"]

                if should_send_watchlist_alert(pair, direction):
                    message = format_watchlist_alert(bias)
                    send_telegram_message(message)
                    print(f"Watchlist alert sent for {pair}", flush=True)
                else:
                    print(f"Duplicate watchlist alert blocked for {pair}", flush=True)

            else:
                print(f"{pair} is not aligned.", flush=True)

        except Exception as e:
            print(f"Error on {pair}: {e}", flush=True)
            traceback.print_exc()

    print("Bot scan completed.", flush=True)

if __name__ == "__main__":
    run_once()
