def detect_breakout(candles, direction, lookback=20):
    if len(candles) < lookback + 1:
        return None

    recent = candles[-lookback-1:-1]
    last = candles[-1]

    recent_high = max(c["high"] for c in recent)
    recent_low = min(c["low"] for c in recent)

    if direction == "buy" and last["close"] > recent_high:
        return {
            "type": "bos_up",
            "level": recent_high,
            "break_candle": last
        }

    if direction == "sell" and last["close"] < recent_low:
        return {
            "type": "bos_down",
            "level": recent_low,
            "break_candle": last
        }

    return None
