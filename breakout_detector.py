from swing_detector import find_swings

def detect_breakout(candles, direction, breakout_window=8, debug=True):
    if len(candles) < 20:
        if debug:
            print("Breakout debug: not enough candles.", flush=True)
        return None

    swing_highs, swing_lows = find_swings(candles)

    if debug:
        print(
            f"Breakout debug: found {len(swing_highs)} swing highs and {len(swing_lows)} swing lows.",
            flush=True
        )

    if direction == "buy":
        if not swing_highs:
            if debug:
                print("Breakout debug: no swing highs found for buy setup.", flush=True)
            return None

        recent_swings = [s for s in swing_highs if s["index"] < len(candles) - 1]
        if not recent_swings:
            if debug:
                print("Breakout debug: no valid historical swing highs.", flush=True)
            return None

        target_swing = recent_swings[-1]

        if debug:
            print(
                f"Breakout debug: target buy swing high at index={target_swing['index']} price={target_swing['price']}",
                flush=True
            )

        start_index = max(target_swing["index"] + 1, len(candles) - breakout_window)

        for i in range(start_index, len(candles)):
            candle = candles[i]
            if debug:
                print(
                    f"Breakout debug: checking candle index={i} close={candle['close']} against swing high={target_swing['price']}",
                    flush=True
                )

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
            if debug:
                print("Breakout debug: no swing lows found for sell setup.", flush=True)
            return None

        recent_swings = [s for s in swing_lows if s["index"] < len(candles) - 1]
        if not recent_swings:
            if debug:
                print("Breakout debug: no valid historical swing lows.", flush=True)
            return None

        target_swing = recent_swings[-1]

        if debug:
            print(
                f"Breakout debug: target sell swing low at index={target_swing['index']} price={target_swing['price']}",
                flush=True
            )

        start_index = max(target_swing["index"] + 1, len(candles) - breakout_window)

        for i in range(start_index, len(candles)):
            candle = candles[i]
            if debug:
                print(
                    f"Breakout debug: checking candle index={i} close={candle['close']} against swing low={target_swing['price']}",
                    flush=True
                )

            if candle["close"] < target_swing["price"]:
                return {
                    "type": "bos_down",
                    "level": target_swing["price"],
                    "break_candle": candle,
                    "break_index": i,
                    "swing_index": target_swing["index"]
                }

    if debug:
        print("Breakout debug: no candle closed beyond target swing level.", flush=True)

    return None
