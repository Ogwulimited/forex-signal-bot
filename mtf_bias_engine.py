from market_data import fetch_candles

def analyze_trend(candles, lookback=20):
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

    first_half = recent[:lookback // 2]
    second_half = recent[lookback // 2:]

    first_half_high = max(c["high"] for c in first_half)
    second_half_high = max(c["high"] for c in second_half)

    first_half_low = min(c["low"] for c in first_half)
    second_half_low = min(c["low"] for c in second_half)

    first_close = closes[0]
    last_close = closes[-1]

    total_range = max(highs) - min(lows)
    avg_close = sum(closes) / len(closes)
    range_ratio = total_range / avg_close if avg_close else 0

    bullish_structure = second_half_high > first_half_high and second_half_low > first_half_low
    bearish_structure = second_half_high < first_half_high and second_half_low < first_half_low

    bullish_close = last_close > first_close
    bearish_close = last_close < first_close

    prev_highs = highs[:-1]
    prev_lows = lows[:-1]

    bullish_breakout = last_close > max(prev_highs)
    bearish_breakout = last_close < min(prev_lows)

    close_position = 0
    if total_range > 0:
        close_position = (last_close - min(lows)) / total_range

    bullish_close_location = close_position >= 0.7
    bearish_close_location = close_position <= 0.3

    net_move_ratio = abs(last_close - first_close) / total_range if total_range > 0 else 0
    strong_net_move = net_move_ratio >= 0.3

    bullish_score = 0
    bearish_score = 0

    if bullish_structure:
        bullish_score += 1
    if bearish_structure:
        bearish_score += 1

    if bullish_close:
        bullish_score += 1
    if bearish_close:
        bearish_score += 1

    if bullish_breakout:
        bullish_score += 1
    if bearish_breakout:
        bearish_score += 1

    if bullish_close_location:
        bullish_score += 1
    if bearish_close_location:
        bearish_score += 1

    if strong_net_move:
        if bullish_close:
            bullish_score += 1
        elif bearish_close:
            bearish_score += 1

    if bullish_score >= 3 and bullish_score > bearish_score:
        bias = "bullish"
        strength = bullish_score
    elif bearish_score >= 3 and bearish_score > bullish_score:
        bias = "bearish"
        strength = bearish_score
    else:
        bias = "neutral"
        strength = max(bullish_score, bearish_score)

    return {
        "bias": bias,
        "strength": strength,
        "range_ratio": range_ratio
    }

def get_mtf_bias(pair):
    candles_4h = fetch_candles(pair, interval="4h", outputsize=40)
    candles_1h = fetch_candles(pair, interval="1h", outputsize=40)

    data_4h = analyze_trend(candles_4h)
    data_1h = analyze_trend(candles_1h)

    bias_4h = data_4h["bias"]
    bias_1h = data_1h["bias"]

    aligned = (
        bias_4h == bias_1h and
        bias_4h in ["bullish", "bearish"]
    )

    return {
        "pair": pair,
        "bias_4h": bias_4h,
        "bias_1h": bias_1h,
        "strength_4h": data_4h["strength"],
        "strength_1h": data_1h["strength"],
        "range_ratio_4h": data_4h["range_ratio"],
        "range_ratio_1h": data_1h["range_ratio"],
        "aligned": aligned
    }
