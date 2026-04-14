"""
Live 5M scanner – runs every 30 minutes, scans pairs with delays to avoid API rate limits.
"""

import json
import os
import time
from datetime import datetime
from mtf_bias_engine import get_mtf_bias
from signal_dispatcher import generate_signal
from signal_formatter import format_signal
from telegram_sender import send_telegram_message
from signal_state import should_send_signal, mark_signal_sent

# Only scan pairs that are most likely to align (reduce API usage)
PAIRS = ["EURUSD", "GBPUSD"]  # AUDUSD and USDJPY removed for now
DELAY_BETWEEN_PAIRS = 25      # seconds (2 pairs * 2 calls each = 4 calls, well under 8 per minute)

def main():
    print(f"Live 5M scanner started at {datetime.utcnow().isoformat()}")
    signals_found = 0

    for pair in PAIRS:
        print(f"\n--- Checking {pair} ---")
        
        try:
            bias = get_mtf_bias(pair)
        except Exception as e:
            print(f"  ⚠️ Error fetching bias for {pair}: {e}")
            time.sleep(DELAY_BETWEEN_PAIRS)
            continue
        
        if not bias.get('aligned'):
            print(f"  HTF not aligned (4H={bias.get('bias_4h')}, 1H={bias.get('bias_1h')})")
            time.sleep(DELAY_BETWEEN_PAIRS)
            continue
        
        # Generate signal with forced sweep (real breakout required)
        try:
            signal = generate_signal(
                bias,
                debug=False,
                ignore_chop=True,
                force_breakout=False,
                force_sweep=True
            )
        except Exception as e:
            print(f"  ⚠️ Error generating signal: {e}")
            time.sleep(DELAY_BETWEEN_PAIRS)
            continue
        
        if signal:
            direction = signal['direction']
            if should_send_signal(pair, direction):
                message = format_signal(signal)
                send_telegram_message(message)
                print(f"  ✅ SIGNAL SENT: {direction} at {signal['entry']}")
                mark_signal_sent(pair, direction)
                signals_found += 1
            else:
                print(f"  ⏭️ Signal for {pair} {direction} already sent recently")
        else:
            print(f"  ❌ No valid setup")
        
        time.sleep(DELAY_BETWEEN_PAIRS)
    
    print(f"\nScanner finished. Signals sent: {signals_found}")

if __name__ == "__main__":
    main()
