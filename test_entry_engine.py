"""
Manual test script for 5M entry engine.
Runs on a single pair with debug output and optional forced breakout.
"""

from mtf_bias_engine import get_mtf_bias
from signal_dispatcher import generate_signal
from signal_formatter import format_signal
from telegram_sender import send_telegram_message

def test_entry_engine(pair, force_breakout=True):
    """
    Test 5M entry pipeline on a single pair.
    
    Parameters:
    - pair: Forex pair string (e.g., 'EURUSD')
    - force_breakout: if True, simulates breakout when none exists (for debugging)
    """
    print(f"\n--- Testing {pair} with force_breakout={force_breakout} ---")
    
    # Get HTF bias
    bias_data = get_mtf_bias(pair)
    print(f"Bias for {pair}: {bias_data}")
    
    # Generate signal
    signal = generate_signal(
        bias_data,
        debug=True,
        ignore_chop=True,      # Bypass chop filter for testing
        force_breakout=force_breakout
    )
    
    print(f"Generated signal for {pair}: {signal}")
    
    if signal:
        # Format and send to Telegram
        message = format_signal(signal)
        print(f"Telegram message:\n{message}")
        send_telegram_message(message)
        print("Signal sent to Telegram.")
    else:
        print("No valid 5M entry setup found.")
    
    print("--- Test completed ---\n")

if __name__ == "__main__":
    # Change this pair to test different ones
    TEST_PAIR = "USDJPY"   # Try AUDUSD, EURUSD, GBPUSD, USDJPY
    
    # Set force_breakout=True to simulate breakout for debugging
    # Set force_breakout=False to require real market breakout
    test_entry_engine(TEST_PAIR, force_breakout=True)
