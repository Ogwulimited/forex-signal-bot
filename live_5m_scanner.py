"""
Live 5M Scanner - Quantity over Quality
Scans EURUSD, GBPUSD, USDJPY, AUDUSD every 30 minutes.
"""
import time
from mtf_bias_engine import get_mtf_bias
from signal_dispatcher import generate_signal
from telegram_sender import send_telegram_message
from signal_formatter import format_signal
from signal_state import should_send_signal, mark_signal_sent

# Configuration
PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]
DELAY_BETWEEN_PAIRS = 20
DEBUG = True
IGNORE_CHOP = True
FORCE_BREAKOUT = False
FORCE_SWEEP = False

def main():
    print(f"Live 5M scanner started at {time.strftime('%Y-%m-%dT%H:%M:%S')}")
    signals_sent = 0

    for pair in PAIRS:
        print(f"\n--- Checking {pair} ---")
        
        bias_data = get_mtf_bias(pair)
        if not bias_data:
            print(f"  ❌ Failed to get MTF bias for {pair}")
            continue
        
        signal = generate_signal(
            bias_data=bias_data,
            debug=DEBUG,
            ignore_chop=IGNORE_CHOP,
            force_breakout=FORCE_BREAKOUT,
            force_sweep=FORCE_SWEEP
        )
        
        if signal:
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
    
    print(f"\nScanner finished. Signals sent: {signals_sent}")

if __name__ == "__main__":
    main()
