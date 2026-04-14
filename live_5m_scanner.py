"""
Live 5M scanner – runs every 30 minutes, scans all pairs,
sends Telegram signals for valid setups (forced sweep enabled).
"""

import json
import os
from datetime import datetime
from mtf_bias_engine import get_mtf_bias
from signal_dispatcher import generate_signal
from signal_formatter import format_signal
from telegram_sender import send_telegram_message
from signal_state import should_send_signal, mark_signal_sent

# Pairs to scan (only those with reliable data)
PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]

def main():
    print(f"Live 5M scanner started at {datetime.utcnow().isoformat()}")
    signals_found = 0

    for pair in PAIRS:
        print(f"\n--- Checking {pair} ---")
        
        # Get HTF bias
        bias = get_mtf_bias(pair)
        if not bias.get('aligned'):
            print(f"  HTF not aligned (4H={bias.get('bias_4h')}, 1H={bias.get('bias_1h')})")
            continue
        
        # Generate signal with forced sweep (real breakout required)
        signal = generate_signal(
            bias,
            debug=False,           # set to True for verbose logs
            ignore_chop=True,      # chop filter disabled for now
            force_breakout=False,  # real breakout required
            force_sweep=True       # temporarily force sweep
        )
        
        if signal:
            direction = signal['direction']
            # Check anti-spam
            if should_send_signal(pair, direction):
                # Send to Telegram
                message = format_signal(signal)
                send_telegram_message(message)
                print(f"  ✅ SIGNAL SENT: {direction} at {signal['entry']}")
                mark_signal_sent(pair, direction)
                signals_found += 1
            else:
                print(f"  ⏭️ Signal for {pair} {direction} already sent recently (anti-spam)")
        else:
            print(f"  ❌ No valid setup")
    
    print(f"\nScanner finished. Signals sent: {signals_found}")

if __name__ == "__main__":
    main()
