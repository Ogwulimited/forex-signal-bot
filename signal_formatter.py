"""
Formats trade signals into readable Telegram messages.
"""

def format_signal(signal):
    """
    Convert signal dict to formatted message string.
    
    Expected signal keys:
    - pair: str (e.g., 'EURUSD')
    - direction: str ('buy' or 'sell')
    - entry: float
    - sl: float (stop loss)
    - tp: float (take profit)
    - timeframe: str (e.g., '5M')
    - rr: float (risk/reward ratio)
    """
    # Convert direction to uppercase for display
    direction_display = signal['direction'].upper()
    
    # Format the message
    message = (
        f"🔔 NEW FOREX SIGNAL\n\n"
        f"Pair: {signal['pair']}\n"
        f"Direction: {direction_display}\n"
        f"Timeframe: {signal['timeframe']}\n"
        f"Entry: {signal['entry']:.5f}\n"
        f"Stop Loss: {signal['sl']:.5f}\n"
        f"Take Profit: {signal['tp']:.5f}\n"
        f"Risk/Reward: 1:{signal['rr']:.1f}\n\n"
        f"#Forex #{signal['pair']} #{direction_display}"
    )
    return message
