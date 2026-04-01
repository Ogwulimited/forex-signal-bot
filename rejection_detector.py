def detect_rejection_candle(candles, direction):
    candle = candles[-1]

    body = abs(candle["close"] - candle["open"])
    upper_wick = candle["high"] - max(candle["open"], candle["close"])
    lower_wick = min(candle["open"], candle["close"]) - candle["low"]

    if body <= 0:
        return None

    if direction == "buy":
        bullish_body = candle["close"] > candle["open"]
        strong_lower_wick = lower_wick >= body * 1.5
        if bullish_body and strong_lower_wick:
            return {
                "candle": candle,
                "strength": round(lower_wick / body, 2)
            }

    if direction == "sell":
        bearish_body = candle["close"] < candle["open"]
        strong_upper_wick = upper_wick >= body * 1.5
        if bearish_body and strong_upper_wick:
            return {
                "candle": candle,
                "strength": round(upper_wick / body, 2)
            }

    return None
