from market_data import fetch_candles

def detect_swing_bias(candles, lookback=20):
    if len(candles) < lookback:
        return {
            "bias": "neutral",
            "strength": 0,
            "range_ratio": 0
        }

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

    avg_close = sum(closes) / len(closes)
    total_range = max(highs) - min(lows)
    range_ratio = total_range / avg_close if avg_close else 0

    bullish_structure = second_half_high > first_half_high and second_half_low > first_half_low
    bearish_structure = second_half_high < first_half_high and second_half_low < first_half_low

    bullish_close = last_close > first_close
    bearish_close = last_close < first_close

    strength = 0

    if bullish_structure:
        strength += 1
    if bearish_structure:
        strength += 1
    if bullish_close:
        strength += 1
    if bearish_close:
        strength += 1

    if bullish_structure and bullish_close:
        bias = "bullish"
    elif bearish_structure and bearish_close:
        bias = "bearish"
    else:
        bias = "neutral"

    return {
        "bias": bias,
        "strength": strength,
        "range_ratio": range_ratio
    }

def get_mtf_bias(pair):
    candles_4h = fetch_candles(pair, interval="4h", outputsize=40)
    candles_1h = fetch_candles(pair, interval="1h", outputsize=40)

    bias_4h_data = detect_swing_bias(candles_4h)
    bias_1h_data = detect_swing_bias(candles_1h)

    bias_4h = bias_4h_data["bias"]
    bias_1h = bias_1h_data["bias"]

    aligned = (
        bias_4h == bias_1h and
        bias_4h in ["bullish", "bearish"]
    )

    return {
        "pair": pair,
        "bias_4h": bias_4h,
        "bias_1h": bias_1h,
        "strength_4h": bias_4h_data["strength"],
        "strength_1h": bias_1h_data["strength"],
        "range_ratio_4h": bias_4h_data["range_ratio"],
        "range_ratio_1h": bias_1h_data["range_ratio"],
        "aligned": aligned
    }
