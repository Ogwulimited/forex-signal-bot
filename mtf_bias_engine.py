from market_data import fetch_candles

def detect_simple_trend(candles, lookback=20):
    if len(candles) < lookback:
        return "neutral"

    recent = candles[-lookback:]
    first_close = recent[0]["close"]
    last_close = recent[-1]["close"]

    highs = [c["high"] for c in recent]
    lows = [c["low"] for c in recent]

    if last_close > first_close and recent[-1]["high"] >= max(highs[:-1]):
        return "bullish"

    if last_close < first_close and recent[-1]["low"] <= min(lows[:-1]):
        return "bearish"

    return "neutral"

def get_mtf_bias(pair):
    candles_4h = fetch_candles(pair, interval="4h", outputsize=50)
    candles_1h = fetch_candles(pair, interval="1h", outputsize=50)

    bias_4h = detect_simple_trend(candles_4h)
    bias_1h = detect_simple_trend(candles_1h)

    aligned = (
        bias_4h == bias_1h and
        bias_4h in ["bullish", "bearish"]
    )

    return {
        "pair": pair,
        "bias_4h": bias_4h,
        "bias_1h": bias_1h,
        "aligned": aligned
                 }
