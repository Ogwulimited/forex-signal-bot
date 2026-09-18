"""
Trendline Detector

Finds and scores trendlines from swing anchors.
Returns the best support and resistance trendlines.

A trendline is:
  - SUPPORT: drawn through swing lows (ascending in uptrend)
  - RESISTANCE: drawn through swing highs (descending during pullbacks in uptrend)

Strategy role:
  - Break of SUPPORT in an uptrend  → REVERSAL setup
  - Break of RESISTANCE in an uptrend → CONTINUATION setup
  - (Mirror for downtrend)
"""

from swing_detector import find_swing_highs, find_swing_lows


def _linear_fit(points):
    """Least-squares fit y = mx + b. Returns (slope, intercept) or None."""
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


def _evaluate_line(candles, slope, intercept, side, tolerance_pct=0.0005):
    """
    Count touches and violations of a trendline.
    side='high' → trendline through candle highs (resistance).
    side='low'  → trendline through candle lows (support).
    """
    touches = 0
    violations = 0
    for i, c in enumerate(candles):
        line_y = slope * i + intercept
        if line_y <= 0:
            continue
        if side == "high":
            if abs(c["high"] - line_y) / line_y < tolerance_pct:
                touches += 1
            if c["close"] > line_y * (1 + tolerance_pct):
                violations += 1
        else:
            if abs(c["low"] - line_y) / line_y < tolerance_pct:
                touches += 1
            if c["close"] < line_y * (1 - tolerance_pct):
                violations += 1
    return touches, violations


def find_best_trendline(candles, side="high", lookback=100,
                        min_touches=2, max_violations=1, debug=False):
    """
    Find the best-scoring trendline on one side.
    Returns dict or None.
    """
    if len(candles) < 20:
        return None

    window = candles[-lookback:]

    if side == "high":
        swings = find_swing_highs(window, left=2, right=2)
    else:
        swings = find_swing_lows(window, left=2, right=2)

    if len(swings) < min_touches:
        if debug:
            print(f"  [TL-{side}] not enough swings ({len(swings)})")
        return None

    recent = swings[-6:] if len(swings) > 6 else swings

    best = None
    best_score = -1

    for i in range(len(recent) - 1):
        for j in range(i + 1, len(recent)):
            a, b = recent[i], recent[j]
            if a["index"] == b["index"]:
                continue
            fit = _linear_fit([(a["index"], a["level"]), (b["index"], b["level"])])
            if fit is None:
                continue
            slope, intercept = fit

            touches, violations = _evaluate_line(window, slope, intercept, side)
            if touches < min_touches or violations > max_violations:
                continue

            # Score: touches weighted positively, violations negatively, span positively
            span = abs(b["index"] - a["index"])
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

    if debug and best:
        print(f"  [TL-{side}] best: score={best['score']} "
              f"touches={best['touches']} violations={best['violations']} "
              f"slope={best['slope']:.6f}")
    return best


def find_trendlines(candles, lookback=100, debug=False):
    """
    Return both resistance (through highs) and support (through lows) trendlines.
    """
    resistance = find_best_trendline(candles, side="high", lookback=lookback, debug=debug)
    support = find_best_trendline(candles, side="low", lookback=lookback, debug=debug)
    return {
        "resistance": resistance,
        "support": support,
    }


def price_at(trendline, index):
    """Given a trendline dict, return the line's y-value at candle index."""
    if trendline is None:
        return None
    return trendline["slope"] * index + trendline["intercept"]
