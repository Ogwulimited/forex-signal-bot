"""
Live 5M Scanner – Quality over Quantity
Scans multiple pairs via Deriv (no rate limits).
"""
import time
import os
from mtf_bias_engine import get_mtf_bias
from signal_dispatcher import generate_signal
from telegram_sender import send_telegram_message
from signal_formatter import format_signal
from signal_state import should_send_signal, mark_signal_sent

# Debug: environment check
print(f"DEBUG ENV: BOT_TOKEN present: {bool(os.getenv('BOT_TOKEN'))}")
print(f"DEBUG ENV: CHAT_ID present: {bool(os.getenv('CHAT_ID'))}")

# ---- EXPANDED PAIR LIST ----
PAIRS = [
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD",
    "USDCAD", "USDCHF", "NZDUSD",
    "EURGBP", "EURJPY", "GBPJPY", "AUDJPY",
    "EURAUD", "EURCHF", "CADJPY", "CHFJPY",
]

# Deriv has generous limits – 3s delay is plenty
DELAY_BETWEEN_PAIRS = 3

# Strict quality settings
DEBUG = True
IGNORE_CHOP = False        # Chop filter ON – rejects choppy markets
FORCE_BREAKOUT = False
FORCE_SWEEP = False

def main():
    print(f"Live 5M scanner started at {time.strftime('%Y-%m-%dT%H:%M:%S')}")
    signals_sent = 0
    setups_found = 0

    for pair in PAIRS:
        print(f"\n--- Checking {pair} ---")

        try:
            bias_data = get_mtf_bias(pair)
        except Exception as e:
            print(f"  ❌ MTF bias failed for {pair}: {e}")
            continue

        if not bias_data:
            print(f"  ❌ No bias data for {pair}")
            continue

        try:
            signal = generate_signal(
                bias_data=bias_data,
                debug=DEBUG,
                ignore_chop=IGNORE_CHOP,
                force_breakout=FORCE_BREAKOUT,
                force_sweep=FORCE_SWEEP
            )
        except Exception as e:
            print(f"  ❌ Signal generation failed for {pair}: {e}")
            continue

        if signal:
            setups_found += 1
            if should_send_signal(pair, signal['direction']):
                message = format_signal(signal)
                try:
                    send_telegram_message(message)
                    print(f"  ✅ Signal sent: {signal['direction']} {pair}")
                except Exception as e:
                    print(f"  ⚠️ Telegram send failed: {e}")
                    print(f"  Signal content: {message}")
                mark_signal_sent(pair, signal['direction'])
                signals_sent += 1
            else:
                print(f"  ⏳ Signal suppressed (anti-spam cooldown)")
        else:
            print(f"  ❌ No valid setup")

        if pair != PAIRS[-1]:
            time.sleep(DELAY_BETWEEN_PAIRS)

    print(f"\nScanner finished.")
    print(f"Pairs scanned: {len(PAIRS)} | Setups found: {setups_found} | Signals sent: {signals_sent}")

if __name__ == "__main__":
    main()
