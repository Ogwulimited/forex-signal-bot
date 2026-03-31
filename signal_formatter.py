def format_signal(signal):
    return (
        f"{signal['pair']} {signal['timeframe']}\n\n"
        f"{signal['type']}\n\n"
        f"Entry: {signal['entry']}\n"
        f"SL: {signal['sl']}\n"
        f"TP: {signal['tp']}"
    )
