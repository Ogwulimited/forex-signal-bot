"""
Scenario Classifier

Combines HTF bias (from mtf_bias_engine) + trendlines (from trendline_detector)
to identify which of the 4 scenarios is currently active:

  1. uptrend_continuation   → HTF bullish + resistance broken UP     → BUY
  2. uptrend_reversal       → HTF bullish + support broken DOWN       → SELL
  3. downtrend_continuation → HTF bearish + support broken DOWN       → SELL
  4. downtrend_reversal     → HTF bearish + resistance broken UP      → BUY

Breakout rule (user spec):
  Requires at least N consecutive candles whose OPEN and CLOSE
  are both beyond the trendline. Default N = 2.
"""

from swing_detector import find_swing_highs, find_swing_lows


BREAKOUT_CONFIRM_BARS = 2      # user's rule: at least 2 candles
BREAKOUT_SEARCH_WINDOW = 30    # look at last N 1H candles for the break


def detect_trendline_break(candles, trendline, direction, required_bars=BREAKOUT_CONFIRM_BARS,
                           search_window=BREAKOUT_SEARCH_WINDOW, debug=False):
    """
    Check if a trendline has been broken in the given direction.

    direction: "up"   → price broke ABOVE the line
               "down" → price broke BELOW the line

    Returns dict with break info or None.
    """
    if trendline is None:
        if debug:
            print(f"  [BREAK-{direction.upper()}] no trendline provided")
        return None

    slope = trendline["slope"]
    intercept = trendline["intercept"]
    n = len(candles)

    start = max(0, n - search_window)
    consec = 0
    first_break_idx = None

    for i in range(start, n):
        c = candles[i]
        line_y = slope * i + intercept
        if line_y <= 0:
            consec = 0
            first_break_idx = None
            continue

        if direction == "up":
            beyond = (c["open"] > line_y and c["close"] > line_y)
        else:
            beyond = (c["open"] < line_y and c["close"] < line_y)

        if beyond:
            if consec == 0:
                first_break_idx = i
            consec += 1
            if consec >= required_bars:
                if debug:
                    print(f"  [BREAK-{direction.upper()}] confirmed at candle {i} "
                          f"(line={line_y:.5f}, close={c['close']:.5f}, "
                          f"bars_beyond={consec})")
                return {
                    "direction": direction,
                    "break_confirmed": True,
                    "break_index": i,
                    "break_start_index": first_break_idx,
                    "line_value_at_break": line_y,
                    "consecutive_bars": consec,
                    "price_at_break": c["close"],
                }
        else:
            consec = 0
            first_break_idx = None

    if debug:
        print(f"  [BREAK-{direction.upper()}] no confirmed break "
              f"(need {required_bars} consecutive bodies beyond line)")
    return None


def classify_scenario(bias_data, trendlines, candles_1h, debug=False):
    """
    Determine which scenario is active.

    bias_data: dict from mtf_bias_engine.get_mtf_bias()
    trendlines: dict from trendline_detector.find_trendlines()
    candles_1h: the 1H candles used to draw the trendlines

    Returns dict or None:
    {
        "scenario": "uptrend_continuation" | ...,
        "direction": "buy" | "sell",
        "trendline": <trendline dict that was broken>,
        "break_info": <break dict>,
        "htf_bias": "bullish" | "bearish",
    }
    """
    if not bias_data or not bias_data.get("aligned"):
        if debug:
            print("  [SCENARIO] HTF not aligned → no scenario")
        return None

    htf_bias = bias_data["bias_4h"]
    if htf_bias not in ("bullish", "bearish"):
        return None

    resistance = trendlines.get("resistance")
    support = trendlines.get("support")

    if debug:
        print(f"  [SCENARIO] HTF bias = {htf_bias}")

    break_up = detect_trendline_break(candles_1h, resistance, "up", debug=debug)
    break_down = detect_trendline_break(candles_1h, support, "down", debug=debug)

    if htf_bias == "bullish":
        if break_up:
            if debug:
                print("  [SCENARIO] → uptrend_continuation (BUY)")
            return {
                "scenario": "uptrend_continuation",
                "direction": "buy",
                "trendline": resistance,
                "break_info": break_up,
                "htf_bias": htf_bias,
            }
        if break_down:
            if debug:
                print("  [SCENARIO] → uptrend_reversal (SELL)")
            return {
                "scenario": "uptrend_reversal",
                "direction": "sell",
                "trendline": support,
                "break_info": break_down,
                "htf_bias": htf_bias,
            }
    else:  # bearish
        if break_down:
            if debug:
                print("  [SCENARIO] → downtrend_continuation (SELL)")
            return {
                "scenario": "downtrend_continuation",
                "direction": "sell",
                "trendline": support,
                "break_info": break_down,
                "htf_bias": htf_bias,
            }
        if break_up:
            if debug:
                print("  [SCENARIO] → downtrend_reversal (BUY)")
            return {
                "scenario": "downtrend_reversal",
                "direction": "buy",
                "trendline": resistance,
                "break_info": break_up,
                "htf_bias": htf_bias,
            }

    if debug:
        print("  [SCENARIO] no confirmed break on either side")
    return None


def find_protected_level(candles, direction, break_index, lookback=60):
    """
    Find the protected swing level for SL placement.

    For a BUY (continuation or reversal): protected LOW
        → most recent swing low before the break
    For a SELL: protected HIGH
        → most recent swing high before the break

    Returns dict {'level': price, 'index': i, 'type': 'high'|'low'} or None.
    """
    if break_index is None or break_index < 10:
        return None

    window_start = max(0, break_index - lookback)
    window = candles[window_start:break_index]

    if len(window) < 10:
        return None

    if direction == "buy":
        swings = find_swing_lows(window, left=2, right=2)
        if not swings:
            return None
        # last swing low before the break
        target = max(swings, key=lambda s: s["index"])
        return {
            "level": target["level"],
            "index": target["index"] + window_start,
            "type": "low",
        }
    else:  # sell
        swings = find_swing_highs(window, left=2, right=2)
        if not swings:
            return None
        target = max(swings, key=lambda s: s["index"])
        return {
            "level": target["level"],
            "index": target["index"] + window_start,
            "type": "high",
}
