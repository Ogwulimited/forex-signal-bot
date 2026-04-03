from swing_detector import find_swings

def detect_breakout(candles, direction, breakout_window=8):
    if len(candles) < 20:
        return None

    swing_highs, swing_lows = find_swings(candles)

    if direction == "buy":
        if not swing_highs:
            return None

        recent_swings = [s for s in swing_highs if s["index"] < len(candles) - 1]
        if not recent_swings:
            return None

        target_swing = recent_swings[-1]

        start_index = max(target_swing["index"] + 1, len(candles) - breakout_window)

        for i in range(start_index, len(candles)):
            candle = candles[i]
            if candle["close"] > target_swing["price"]:
                return {
                    "type": "bos_up",
                    "level": target_swing["price"],
                    "break_candle": candle,
                    "break_index": i,
                    "swing_index": target_swing["index"]
                }

    elif direction == "sell":
        if not swing_lows:
            return None

        recent_swings = [s for s in swing_lows if s["index"] < len(candles) - 1]
        if not recent_swings:
            return None

        target_swing = recent_swings[-1]

        start_index = max(target_swing["index"] + 1, len(candles) - breakout_window)

        for i in range(start_index, len(candles)):
            candle = candles[i]
            if candle["close"] < target_swing["price"]:
                return {
                    "type": "bos_down",
                    "level": target_swing["price"],
                    "break_candle": candle,
                    "break_index": i,
                    "swing_index": target_swing["index"]
                }

    return None
