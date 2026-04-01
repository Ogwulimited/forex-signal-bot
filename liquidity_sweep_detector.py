def detect_liquidity_sweep(candles, direction, lookback=10):
    if len(candles) < lookback + 1:
        return None

    recent = candles[-lookback-1:-1]
    last = candles[-1]

    recent_high = max(c["high"] for c in recent)
    recent_low = min(c["low"] for c in recent)

    if direction == "buy":
        swept = last["low"] < recent_low
        reclaimed = last["close"] > recent_low
        if swept and reclaimed:
            return {
                "type": "sell_side_sweep",
                "level": recent_low,
                "sweep_candle": last
            }

    if direction == "sell":
        swept = last["high"] > recent_high
        reclaimed = last["close"] < recent_high
        if swept and reclaimed:
            return {
                "type": "buy_side_sweep",
                "level": recent_high,
                "sweep_candle": last
            }

    return None
