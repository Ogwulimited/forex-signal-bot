import traceback
from mtf_bias_engine import get_mtf_bias

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
            else:
                print(f"{pair} is not aligned.", flush=True)

        except Exception as e:
            print(f"Error on {pair}: {e}", flush=True)
            traceback.print_exc()

    print("Bot scan completed.", flush=True)

if __name__ == "__main__":
    run_once()
