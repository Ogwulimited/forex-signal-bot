"""
Trendline Detector v3

- Loosened violation tolerance (allows noise)
- Requires no long streaks of violations
- Wider lookback window
"""

from swing_detector import find_swing_highs, find_swing_lows


MIN_SLOPE_PCT = 0.00001
TOLERANCE_PCT = 0.0003
MIN_TOUCHES = 3
MAX_VIOLATIONS = 5
MAX_CONSECUTIVE_VIOLATIONS = 3
MIN_SPAN = 10


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


def _count_touches_and_violations(candles, swings, slope, intercept, side, tolerance_pct):
    touches = 0
    for s in swings:
        line_y = _line_value(slope, intercept, s["index"])
        if line_y <= 0:
            continue
        if abs(s["level"] - line_y) / line_y < tolerance_pct:
            touches += 1

    violations = 0
    max_consecutive = 0
    current_streak = 0

    for i, c in enumerate(candles):
        line_y = _line_value(slope, intercept, i)
        if line_y <= 0:
            current_streak = 0
            continue
        is_violation = False
        if side == "high":
            if c["close"] > line_y * (1 + tolerance_pct):
                is_violation = True
        else:
            if c["close"] < line_y * (1 - tolerance_pct):
                is_violation = True

        if is_violation:
            violations += 1
            current_streak += 1
            if current_streak > max_consecutive:
                max_consecutive = current_streak
        else:
            current_streak = 0

    return touches, violations, max_consecutive


def find_best_trendline(candles, side="high", lookback=250,
                        min_touches=MIN_TOUCHES,
                        max_violations=MAX_VIOLATIONS,
                        max_consecutive=MAX_CONSECUTIVE_VIOLATIONS,
                        min_span=MIN_SPAN,
                        debug=False):
    if len(candles) < 20:
        return None

    window = candles[-lookback:]
    avg_price = sum(c["close"] for c in window) / len(window)
    min_slope_abs = avg_price * MIN_SLOPE_PCT

    if side == "high":
        swings = find_swing_highs(window, left=2, right=2)
    else:
        swings = find_swing_lows(window, left=2, right=2)

    if debug:
        print(f"  [TL-{side}] swings={len(swings)} avg_price={avg_price:.5f}")

    if len(swings) < min_touches:
        return None

    recent = swings[-10:] if len(swings) > 10 else swings

    best = None
    best_score = -1
    tested = 0
    rej_slope = 0
    rej_span = 0
    rej_touch = 0
    rej_viol = 0
    rej_consec = 0

    for i in range(len(recent) - 1):
        for j in range(i + 1, len(recent)):
            a, b = recent[i], recent[j]
            if a["index"] == b["index"]:
                continue
            span = abs(b["index"] - a["index"])
            if span < min_span:
                rej_span += 1
                continue

            fit = _linear_fit([(a["index"], a["level"]), (b["index"], b["level"])])
            if fit is None:
                continue
            slope, intercept = fit

            if abs(slope) < min_slope_abs:
                rej_slope += 1
                continue

            touches, violations, consec = _count_touches_and_violations(
                window, swings, slope, intercept, side, TOLERANCE_PCT
            )
            tested += 1

            if touches < min_touches:
                rej_touch += 1
                continue
            if violations > max_violations:
                rej_viol += 1
                continue
            if consec > max_consecutive:
                rej_consec += 1
                continue

            score = touches * 10 - violations * 5 + min(span, 100)

            if score > best_score:
                best_score = score
                best = {
                    "slope": slope,
                    "intercept": intercept,
                    "side": side,
                    "touches": touches,
                    "violations": violations,
                    "max_consecutive_violations": consec,
                    "span": span,
                    "score": score,
                    "anchor_a_idx": a["index"],
                    "anchor_b_idx": b["index"],
                    "anchor_a_price": a["level"],
                    "anchor_b_price": b["level"],
                }

    if debug:
        print(f"  [TL-{side}] tested={tested} | "
              f"rej_span={rej_span} rej_slope={rej_slope} "
              f"rej_touch={rej_touch} rej_viol={rej_viol} rej_consec={rej_consec}")
        if best:
            print(f"  [TL-{side}] WINNER: score={best['score']} "
                  f"touches={best['touches']} violations={best['violations']} "
                  f"max_consec={best['max_consecutive_violations']} "
                  f"span={best['span']} slope={best['slope']:.6f}")
        else:
            print(f"  [TL-{side}] no winner")

    return best


def find_trendlines(candles, lookback=250, debug=False):
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
