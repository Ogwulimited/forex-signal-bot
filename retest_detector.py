def detect_retest(candles, breakout, direction, tolerance_ratio=0.0007, recent_bars=5):
    level = breakout["level"]
    recent = candles[-recent_bars:]

    for candle in recent:
        price = candle["close"]
        tolerance = price * tolerance_ratio

        if direction == "buy":
            touched = candle["low"] <= level + tolerance
            held = candle["close"] > level
            if touched and held:
                return {
                    "level": level,
                    "retest_candle": candle
                }

        if direction == "sell":
            touched = candle["high"] >= level - tolerance
            held = candle["close"] < level
            if touched and held:
                return {
                    "level": level,
                    "retest_candle": candle
                }

    return None
