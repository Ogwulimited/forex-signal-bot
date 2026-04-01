def format_watchlist_alert(bias):
    direction = "BULLISH" if bias["bias_4h"] == "bullish" else "BEARISH"

    return (
        f"WATCHLIST ALERT\n\n"
        f"Pair: {bias['pair']}\n"
        f"4H Bias: {bias['bias_4h']}\n"
        f"1H Bias: {bias['bias_1h']}\n"
        f"Direction: {direction}\n\n"
        f"Status: Await 5M breakout + retest confirmation"
    )
