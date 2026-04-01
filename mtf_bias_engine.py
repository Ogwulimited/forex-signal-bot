from market_data import fetch_candles

def detect_swing_bias(candles, lookback=20):
    if len(candles) < lookback:
        return "neutral"

    recent = candles[-lookback:]

    highs = [c["high"] for c in recent]
    lows = [c["low"] for c in recent]
    closes = [c["close"] for c in recent]

    first_half_high = max(highs[:lookback // 2])
    second_half_high = max(highs[lookback // 2:])

    first_half_low = min(lows[:lookback // 2])
    second_half_low = min(lows[lookback // 2:])

    first_close = closes[0]
    last_close = closes[-1]

    bullish_structure = second_half_high > first_half_high and second_half_low > first_half_low
    bearish_structure = second_half_high < first_half_high and second_half_low < first_half_low

    bullish_close = last_close > first_close
    bearish_close = last_close < first_close

    if bullish_structure and bullish_close:
        return "bullish"

    if bearish_structure and bearish_close:
        return "bearish"

    return "neutral"

def get_mtf_bias(pair):
    candles_4h = fetch_candles(pair, interval="4h", outputsize=40)
    candles_1h = fetch_candles(pair, interval="1h", outputsize=40)

    bias_4h = detect_swing_bias(candles_4h)
    bias_1h = detect_swing_bias(candles_1h)

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
