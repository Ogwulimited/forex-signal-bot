def format_new_signal(trade, pair, timeframe):
    direction = "BUY" if trade["direction"] == "bullish" else "SELL"

    return f"""
{pair} {timeframe}

{direction}

Entry: {trade['entry']}
SL: {trade['stop_loss']}
TP: {trade['take_profit']}
"""
