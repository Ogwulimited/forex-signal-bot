"""
Manual test script for 5M entry engine.
Runs on a single pair with debug output and optional forced breakout/sweep.
"""

from mtf_bias_engine import get_mtf_bias
from signal_dispatcher import generate_signal
from signal_formatter import format_signal
from telegram_sender import send_telegram_message

def test_entry_engine(pair, force_breakout=True, force_sweep=True):
    """
    Test 5M entry pipeline on a single pair.
    
    Parameters:
    - pair: Forex pair string (e.g., 'EURUSD')
    - force_breakout: if True, simulates breakout when none exists (for debugging)
    - force_sweep: if True, simulates liquidity sweep when none exists (for debugging)
    """
    print(f"\n--- Testing {pair} with force_breakout={force_breakout}, force_sweep={force_sweep} ---")
    
    # Get HTF bias
    bias_data = get_mtf_bias(pair)
    print(f"Bias for {pair}: {bias_data}")
    
    # Generate signal
    signal = generate_signal(
        bias_data,
        debug=True,
        ignore_chop=True,
        force_breakout=force_breakout,
        force_sweep=force_sweep
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
    TEST_PAIR = "EURUSD"   # Try AUDUSD, EURUSD, GBPUSD, USDJPY
    
    # Real market test – no forced data
    test_entry_engine(TEST_PAIR, force_breakout=False, force_sweep=False)
