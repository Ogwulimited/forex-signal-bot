def find_swings(candles, left=2, right=2):
    swing_highs = []
    swing_lows = []

    for i in range(left, len(candles) - right):
        current_high = candles[i]["high"]
        current_low = candles[i]["low"]

        left_highs = [candles[j]["high"] for j in range(i - left, i)]
        right_highs = [candles[j]["high"] for j in range(i + 1, i + 1 + right)]

        left_lows = [candles[j]["low"] for j in range(i - left, i)]
        right_lows = [candles[j]["low"] for j in range(i + 1, i + 1 + right)]

        if current_high > max(left_highs) and current_high > max(right_highs):
            swing_highs.append({
                "index": i,
                "price": current_high,
                "candle": candles[i]
            })

        if current_low < min(left_lows) and current_low < min(right_lows):
            swing_lows.append({
                "index": i,
                "price": current_low,
                "candle": candles[i]
            })

    return swing_highs, swing_lows
