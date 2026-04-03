from swing_detector import find_swings

def detect_breakout(candles, direction, breakout_window=8, min_bars_after_swing=5, debug=True):
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

    cutoff_index = len(candles) - min_bars_after_swing

    if direction == "buy":
        usable_swings = [s for s in swing_highs if s["index"] < cutoff_index]

        if not usable_swings:
            if debug:
                print("Breakout debug: no usable swing highs found for buy setup.", flush=True)
            return None

        target_swing = usable_swings[-1]

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
        usable_swings = [s for s in swing_lows if s["index"] < cutoff_index]

        if not usable_swings:
            if debug:
                print("Breakout debug: no usable swing lows found for sell setup.", flush=True)
            return None

        target_swing = usable_swings[-1]

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
