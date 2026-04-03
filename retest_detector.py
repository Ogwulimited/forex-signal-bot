def detect_retest(candles, breakout, direction, tolerance_ratio=0.0007, max_retest_bars=6):
    level = breakout["level"]
    break_index = breakout["break_index"]

    start = break_index + 1
    end = min(len(candles), break_index + 1 + max_retest_bars)

    if start >= len(candles):
        return None

    for i in range(start, end):
        candle = candles[i]
        price = candle["close"]
        tolerance = price * tolerance_ratio

        if direction == "buy":
            touched_zone = candle["low"] <= level + tolerance
            held_above = candle["close"] > level

            if touched_zone and held_above:
                return {
                    "level": level,
                    "retest_candle": candle,
                    "retest_index": i
                }

        if direction == "sell":
            touched_zone = candle["high"] >= level - tolerance
            held_below = candle["close"] < level

            if touched_zone and held_below:
                return {
                    "level": level,
                    "retest_candle": candle,
                    "retest_index": i
                }

    return None
