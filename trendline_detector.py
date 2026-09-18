"""
Trendline Detector v2

Finds trendlines anchored on swing points, requires meaningful slope,
and counts touches only at swing points (not arbitrary candles).

- SUPPORT: line through swing lows
- RESISTANCE: line through swing highs
"""

from swing_detector import find_swing_highs, find_swing_lows


MIN_SLOPE_PCT = 0.00001   # min |slope| per candle, relative to price
TOLERANCE_PCT = 0.0003    # touch tolerance
MIN_TOUCHES = 3           # minimum swing-point touches
MAX_VIOLATIONS = 1
MIN_SPAN = 20             # min candles spanned by anchors


def _linear_fit(points):
    n = len(points)
    if n < 2:
        return None
    sum_x = sum(p[0] for p in points)
    sum_y = sum(p[1] for p in points)
    sum_xy = sum(p[0] * p[1] for p in points)
    sum_xx = sum(p[0] * p[0] for p in points)
    denom = n * sum_xx - sum_x * sum_x
    if denom == 0:
        return None
    slope = (n * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / n
    return slope, intercept


def _line_value(slope, intercept, x):
    return slope * x + intercept


def _count_swing_touches(candles, swings, slope, intercept, side, tolerance_pct):
    """Count touches only at swing points, and violations at close prices."""
    touches = 0
    for s in swings:
        line_y = _line_value(slope, intercept, s["index"])
        if line_y <= 0:
            continue
        if abs(s["level"] - line_y) / line_y < tolerance_pct:
            touches += 1

    violations = 0
    for i, c in enumerate(candles):
        line_y = _line_value(slope, intercept, i)
        if line_y <= 0:
            continue
        if side == "high":
            if c["close"] > line_y * (1 + tolerance_pct):
                violations += 1
        else:
            if c["close"] < line_y * (1 - tolerance_pct):
                violations += 1
    return touches, violations


def find_best_trendline(candles, side="high", lookback=100,
                        min_touches=MIN_TOUCHES,
                        max_violations=MAX_VIOLATIONS,
                        min_span=MIN_SPAN,
                        debug=False):
    if len(candles) < 20:
        if debug:
            print(f"  [TL-{side}] not enough candles ({len(candles)})")
        return None

    window = candles[-lookback:]
    avg_price = sum(c["close"] for c in window) / len(window)
    min_slope_abs = avg_price * MIN_SLOPE_PCT

    if side == "high":
        swings = find_swing_highs(window, left=2, right=2)
    else:
        swings = find_swing_lows(window, left=2, right=2)

    if debug:
        print(f"  [TL-{side}] found {len(swings)} swings, avg_price={avg_price:.5f}")

    if len(swings) < min_touches:
        if debug:
            print(f"  [TL-{side}] fewer swings ({len(swings)}) than min_touches ({min_touches})")
        return None

    recent = swings[-8:] if len(swings) > 8 else swings

    best = None
    best_score = -1
    tested = 0
    rejected_slope = 0
    rejected_span = 0
    rejected_touches = 0
    rejected_violations = 0

    for i in range(len(recent) - 1):
        for j in range(i + 1, len(recent)):
            a, b = recent[i], recent[j]
            if a["index"] == b["index"]:
                continue
            span = abs(b["index"] - a["index"])
            if span < min_span:
                rejected_span += 1
                continue

            fit = _linear_fit([(a["index"], a["level"]), (b["index"], b["level"])])
            if fit is None:
                continue
            slope, intercept = fit

            if abs(slope) < min_slope_abs:
                rejected_slope += 1
                continue

            touches, violations = _count_swing_touches(
                window, swings, slope, intercept, side, TOLERANCE_PCT
            )
            tested += 1

            if touches < min_touches:
                rejected_touches += 1
                continue
            if violations > max_violations:
                rejected_violations += 1
                continue

            score = touches * 10 - violations * 20 + min(span, 100)

            if score > best_score:
                best_score = score
                best = {
                    "slope": slope,
                    "intercept": intercept,
                    "side": side,
                    "touches": touches,
                    "violations": violations,
                    "span": span,
                    "score": score,
                    "anchor_a_idx": a["index"],
                    "anchor_b_idx": b["index"],
                    "anchor_a_price": a["level"],
                    "anchor_b_price": b["level"],
                }

    if debug:
        print(f"  [TL-{side}] candidates tested={tested} | "
              f"rejected slope={rejected_slope} span={rejected_span} "
              f"touches={rejected_touches} violations={rejected_violations}")
        if best:
            print(f"  [TL-{side}] WINNER: score={best['score']} "
                  f"touches={best['touches']} violations={best['violations']} "
                  f"slope={best['slope']:.6f}")
        else:
            print(f"  [TL-{side}] no winner")

    return best


def find_trendlines(candles, lookback=100, debug=False):
    resistance = find_best_trendline(candles, side="high", lookback=lookback, debug=debug)
    support = find_best_trendline(candles, side="low", lookback=lookback, debug=debug)
    return {
        "resistance": resistance,
        "support": support,
    }


def price_at(trendline, index):
    if trendline is None:
        return None
    return trendline["slope"] * index + trendline["intercept"]
