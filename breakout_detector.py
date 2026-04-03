def detect_breakout(candles, direction, lookback=20, breakout_window=8):
    if len(candles) < lookback + breakout_window:
        return None

    start_index = len(candles) - breakout_window

    for i in range(start_index, len(candles)):
        breakout_candle = candles[i]
        history = candles[i - lookback:i]

        if len(history) < lookback:
            continue

        history_high = max(c["high"] for c in history)
        history_low = min(c["low"] for c in history)

        if direction == "buy":
            broke = breakout_candle["close"] > history_high
            if broke:
                return {
                    "type": "bos_up",
                    "level": history_high,
                    "break_candle": breakout_candle,
                    "break_index": i
                }

        if direction == "sell":
            broke = breakout_candle["close"] < history_low
            if broke:
                return {
                    "type": "bos_down",
                    "level": history_low,
                    "break_candle": breakout_candle,
                    "break_index": i
                }

    return None
