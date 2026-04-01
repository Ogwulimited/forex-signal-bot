from market_data import fetch_candles

def generate_signal(bias):
    if not bias.get("aligned"):
        return None

    pair = bias["pair"]
    direction = "BUY" if bias["bias_4h"] == "bullish" else "SELL"

    candles_5m = fetch_candles(pair, interval="5min", outputsize=50)

    # Placeholder for upcoming full strategy logic
    # For now, do not send any real signal yet
    return None
