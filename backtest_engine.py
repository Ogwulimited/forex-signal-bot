"""
Backtest Engine - Funnel Diagnostic for Trendline Breakout + Retest Strategy

Walks historical 5M candles pair-by-pair, reconstructs the live pipeline
at each scan point, and counts which stage each setup dies at.

Output:
  - backtest_report.md
  - backtest_funnel.json

Run via GitHub Actions workflow "Backtest Strategy" (manual trigger).
"""

import json
import time
from collections import Counter
from datetime import datetime, timezone

import websocket

from mtf_bias_engine import analyze_trend
from breakout_detector import detect_breakout
from retest_detector import detect_retest
from rejection_detector import detect_rejection
from liquidity_sweep_detector import detect_liquidity_sweep
from rr_calculator import calculate_rr
from chop_filter import is_choppy


# =============================================================
# CONFIGURATION
# =============================================================

PAIRS = [
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD",
    "USDCHF", "NZDUSD", "EURGBP", "EURJPY", "GBPJPY",
    "AUDJPY", "EURAUD", "EURCHF", "CADJPY", "CHFJPY",
]

MONTHS_BACK = 3
SCAN_EVERY_N_BARS = 5      # check every 5th 5M candle (~every 25 min)
WINDOW_5M = 100
WINDOW_4H = 40
WINDOW_1H = 40

# Strategy parameters (must match production)
BREAKOUT_WINDOW = 5
MIN_BARS_AFTER_SWING = 3
RETEST_TOLERANCE_RATIO = 0.0003
RETEST_MAX_BARS = 10
RR_MIN = 2.0
CHOP_LOOKBACK = 20
CHOP_MIN_RANGE_RATIO = 0.0005


# =============================================================
# DERIV DATA LOADER
# =============================================================

WS_URL = "wss://api.derivws.com/trading/v1/options/ws/public"

SYMBOL_MAP = {
    "EURUSD": "frxEURUSD", "GBPUSD": "frxGBPUSD", "USDJPY": "frxUSDJPY",
    "AUDUSD": "frxAUDUSD", "USDCAD": "frxUSDCAD", "USDCHF": "frxUSDCHF",
    "NZDUSD": "frxNZDUSD", "EURGBP": "frxEURGBP", "EURJPY": "frxEURJPY",
    "GBPJPY": "frxGBPJPY", "AUDJPY": "frxAUDJPY", "EURAUD": "frxEURAUD",
    "EURCHF": "frxEURCHF", "CADJPY": "frxCADJPY", "CHFJPY": "frxCHFJPY",
}

GRANULARITY = {"5min": 300, "1h": 3600, "4h": 14400}
CANDLES_PER_DAY = {"5min": 288, "1h": 24, "4h": 6}


def _fetch_chunk(symbol, granularity, count, end):
    ws = websocket.create_connection(WS_URL, timeout=30)
    request = {
        "ticks_history": symbol,
        "adjust_start_time": 1,
        "count": count,
        "end": end,
        "style": "candles",
        "granularity": granularity,
    }
    ws.send(json.dumps(request))
    for _ in range(5):
        raw = ws.recv()
        resp = json.loads(raw)
        if "candles" in resp:
            ws.close()
            return resp["candles"]
        if "error" in resp:
            ws.close()
            raise Exception(f"Deriv error: {resp['error']}")
    ws.close()
    return []


def fetch_history(pair, timeframe, months_back):
    symbol = SYMBOL_MAP.get(pair.upper())
    if not symbol:
        raise ValueError(f"Unknown pair: {pair}")
    granularity = GRANULARITY[timeframe]

    days = int(months_back * 30)
    target = CANDLES_PER_DAY[timeframe] * days

    all_candles = []
    end = "latest"
    remaining = target

    while remaining > 0:
        take = min(5000, remaining)
        try:
            chunk = _fetch_chunk(symbol, granularity, take, end)
        except Exception as e:
            print(f"    Fetch error for {pair} {timeframe}: {e}")
            break
        if not chunk:
            break
        all_candles = chunk + all_candles
        remaining -= len(chunk)
        if len(chunk) < take:
            break
        earliest = int(chunk[0]["epoch"])
        end = earliest - 1
        time.sleep(0.3)

    return [
        {
            "datetime": int(c["epoch"]),
            "open": float(c["open"]),
            "high": float(c["high"]),
            "low": float(c["low"]),
            "close": float(c["close"]),
        }
        for c in all_candles
    ]


# =============================================================
# STRATEGY REPLAY
# =============================================================

def compute_bias(pair, candles_4h, candles_1h):
    data_4h = analyze_trend(candles_4h)
    data_1h = analyze_trend(candles_1h)
    bias_4h = data_4h["bias"]
    bias_1h = data_1h["bias"]
    aligned = (bias_4h == bias_1h and bias_4h in ["bullish", "bearish"])
    return {
        "pair": pair,
        "bias_4h": bias_4h, "bias_1h": bias_1h,
        "strength_4h": data_4h["strength"], "strength_1h": data_1h["strength"],
        "range_ratio_4h": data_4h["range_ratio"],
        "range_ratio_1h": data_1h["range_ratio"],
        "aligned": aligned,
    }


def run_pipeline(pair, candles_5m, bias_data, current_epoch):
    """Replay of signal_dispatcher.generate_signal, returning the rejecting stage."""
    if not bias_data["aligned"]:
        return "bias_not_aligned"

    direction = "buy" if bias_data["bias_4h"] == "bullish" else "sell"

    # Session filter (07:00–20:00 UTC) — matches live bot
    hour_utc = datetime.fromtimestamp(current_epoch, tz=timezone.utc).hour
    if not (7 <= hour_utc < 20):
        return "session"

    if is_choppy(candles_5m, lookback=CHOP_LOOKBACK, min_range_ratio=CHOP_MIN_RANGE_RATIO):
        return "chop"

    breakout = detect_breakout(
        candles_5m, direction,
        breakout_window=BREAKOUT_WINDOW,
        min_bars_after_swing=MIN_BARS_AFTER_SWING,
        debug=False, force_breakout=False,
    )
    if not breakout:
        return "breakout"

    retest = detect_retest(
        candles_5m, breakout, direction,
        tolerance_ratio=RETEST_TOLERANCE_RATIO,
        max_retest_bars=RETEST_MAX_BARS,
        debug=False,
    )
    if not retest:
        return "retest"

    rejection = detect_rejection(
        candles_5m, direction, retest=retest, breakout=breakout, debug=False,
    )
    if not rejection:
        return "rejection"

    sweep = detect_liquidity_sweep(
        candles_5m, direction,
        breakout=breakout, retest=retest,
        lookback=20, debug=False, force_sweep=False,
    )
    if not sweep:
        return "sweep"

    trade = calculate_rr(
        candles_5m, direction, rejection, sweep, min_rr=RR_MIN, debug=False,
    )
    if not trade:
        return "rr"

    return "signal"


def backtest_pair(pair, data_5m, data_4h, data_1h, verbose=True):
    funnel = Counter()
    stage_order = [
        "bias_not_aligned", "session", "chop",
        "breakout", "retest", "rejection", "sweep", "rr", "signal",
    ]
    for s in stage_order:
        funnel[s] = 0

    if len(data_5m) < WINDOW_5M + 1:
        return funnel

    epochs_4h = [c["datetime"] for c in data_4h]
    epochs_1h = [c["datetime"] for c in data_1h]

    idx_4h = 0
    idx_1h = 0
    scan_points = 0

    for i in range(WINDOW_5M, len(data_5m), SCAN_EVERY_N_BARS):
        t = data_5m[i]["datetime"]

        while idx_4h < len(epochs_4h) and epochs_4h[idx_4h] <= t:
            idx_4h += 1
        while idx_1h < len(epochs_1h) and epochs_1h[idx_1h] <= t:
            idx_1h += 1

        if idx_4h < WINDOW_4H or idx_1h < WINDOW_1H:
            continue

        candles_5m = data_5m[i - WINDOW_5M:i]
        candles_4h = data_4h[idx_4h - WINDOW_4H:idx_4h]
        candles_1h = data_1h[idx_1h - WINDOW_1H:idx_1h]

        bias_data = compute_bias(pair, candles_4h, candles_1h)
        stage = run_pipeline(pair, candles_5m, bias_data, t)
        funnel[stage] += 1
        scan_points += 1

    if verbose:
        print(f"    Scan points evaluated: {scan_points}")
    return funnel


# =============================================================
# REPORT
# =============================================================

def format_report(all_funnels, months_back):
    lines = []
    lines.append("# Backtest Funnel Report\n")
    lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}  ")
    lines.append(f"History window: last {months_back} months  ")
    lines.append(f"Pairs tested: {len(all_funnels)}  ")
    lines.append(f"Scan cadence: every {SCAN_EVERY_N_BARS}th 5M candle "
                 f"(~every {SCAN_EVERY_N_BARS*5} min)\n")

    stages = [
        ("bias_not_aligned", "HTF not aligned"),
        ("session", "Outside London/NY session"),
        ("chop", "Chop filter rejected"),
        ("breakout", "No swing breakout"),
        ("retest", "No real retest"),
        ("rejection", "No rejection candle"),
        ("sweep", "No liquidity sweep"),
        ("rr", "RR below minimum"),
        ("signal", "SIGNAL (all stages passed)"),
    ]

    total = sum(sum(f.values()) for f in all_funnels.values())

    lines.append("## Aggregate Funnel\n")
    lines.append("| Stage | Count | % of scan points |")
    lines.append("|-------|------:|-----------------:|")
    for key, label in stages:
        cnt = sum(f.get(key, 0) for f in all_funnels.values())
        pct = (cnt / total * 100) if total else 0
        lines.append(f"| {label} | {cnt} | {pct:.2f}% |")
    lines.append(f"| **Total scan points** | **{total}** | 100% |\n")

    signals = sum(f.get("signal", 0) for f in all_funnels.values())
    per_month = signals / months_back if months_back else 0
    lines.append(f"**Signal rate:** {signals} signals over {months_back} months "
                 f"= **{per_month:.2f} signals / month** across {len(all_funnels)} pairs\n")

    lines.append("## Per-Pair Funnel\n")
    header = "| Pair | " + " | ".join(label.split()[0] for _, label in stages) + " |"
    sep = "|" + "---|" * (len(stages) + 1)
    lines.append(header)
    lines.append(sep)
    for pair, f in sorted(all_funnels.items()):
        row = [pair] + [str(f.get(k, 0)) for k, _ in stages]
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    lines.append("## Bottleneck Analysis\n")

    aligned = sum(f.get("session", 0) + f.get("chop", 0) + f.get("breakout", 0) +
                  f.get("retest", 0) + f.get("rejection", 0) + f.get("sweep", 0) +
                  f.get("rr", 0) + f.get("signal", 0)
                  for f in all_funnels.values())

    if aligned == 0:
        lines.append("**No setups reached the pipeline.** "
                     "HTF alignment is the bottleneck — no pair had aligned bias "
                     "during the test window.\n")
    else:
        stages_after = [
            ("session", "Session filter"),
            ("chop", "Chop filter"),
            ("breakout", "Breakout"),
            ("retest", "Retest"),
            ("rejection", "Rejection"),
            ("sweep", "Sweep"),
            ("rr", "RR filter"),
        ]
        drops = [(sum(f.get(k, 0) for f in all_funnels.values()), label)
                 for k, label in stages_after]
        drops.sort(reverse=True)

        lines.append(f"Aligned candidates entering the pipeline: **{aligned}**\n")
        lines.append("| Filter | Rejections | % of candidates |")
        lines.append("|--------|-----------:|----------------:|")
        for cnt, label in drops:
            pct = (cnt / aligned * 100) if aligned else 0
            lines.append(f"| {label} | {cnt} | {pct:.1f}% |")
        lines.append("")

        top_cnt, top_label = drops[0]
        top_pct = (top_cnt / aligned * 100) if aligned else 0
        lines.append(f"**Primary bottleneck: {top_label}** — rejected "
                     f"{top_cnt} of {aligned} candidates ({top_pct:.1f}%).\n")

    lines.append("## Interpretation Guide\n")
    lines.append("- **HTF not aligned dominates:** watchlist thresholds may be too strict, "
                 "or pairs are not trending in this window.")
    lines.append("- **Session dominates:** most setups happen outside London/NY hours.")
    lines.append("- **Breakout dominates:** swing definition is too strict, or price "
                 "genuinely does not break structure as often as assumed.")
    lines.append("- **Retest dominates:** tolerance or max bars may be too tight.")
    lines.append("- **Rejection dominates:** wick-ratio threshold may be miscalibrated.")
    lines.append("- **Sweep dominates:** sweep definition may not match real price behavior.")
    lines.append("- **RR dominates:** TP structure may create poor RR on most setups.")
    lines.append("- **Signal count healthy (>1/month):** parameters are calibrated.")
    return "\n".join(lines)


# =============================================================
# MAIN
# =============================================================

def main():
    print("=" * 60)
    print("BACKTEST ENGINE - FUNNEL DIAGNOSTIC")
    print("=" * 60)
    print(f"Pairs: {len(PAIRS)}  |  History: {MONTHS_BACK} months  |  "
          f"Scan cadence: every {SCAN_EVERY_N_BARS}th 5M candle")
    print()

    all_funnels = {}

    for pair in PAIRS:
        print(f"\n--- {pair} ---")
        try:
            print("  Fetching 5M history...")
            data_5m = fetch_history(pair, "5min", MONTHS_BACK)
            print(f"    5M candles: {len(data_5m)}")

            print("  Fetching 1H history...")
            data_1h = fetch_history(pair, "1h", MONTHS_BACK)
            print(f"    1H candles: {len(data_1h)}")

            print("  Fetching 4H history...")
            data_4h = fetch_history(pair, "4h", MONTHS_BACK)
            print(f"    4H candles: {len(data_4h)}")

            if len(data_5m) < WINDOW_5M + 100 or len(data_4h) < WINDOW_4H + 10:
                print(f"    Insufficient history for {pair}, skipping")
                continue

            print("  Replaying pipeline...")
            funnel = backtest_pair(pair, data_5m, data_4h, data_1h, verbose=True)
            all_funnels[pair] = funnel

            del data_5m, data_4h, data_1h
        except Exception as e:
            print(f"  ERROR on {pair}: {e}")
            continue

    print("\n" + "=" * 60)
    print("Writing reports...")

    report = format_report(all_funnels, MONTHS_BACK)
    with open("backtest_report.md", "w") as f:
        f.write(report)

    with open("backtest_funnel.json", "w") as f:
        json.dump({
            "generated": datetime.now(timezone.utc).isoformat(),
            "months_back": MONTHS_BACK,
            "pairs": list(all_funnels.keys()),
            "funnels": {p: dict(f) for p, f in all_funnels.items()},
        }, f, indent=2)

    print("Wrote backtest_report.md and backtest_funnel.json")

    total_signals = sum(f.get("signal", 0) for f in all_funnels.values())
    total_scans = sum(sum(f.values()) for f in all_funnels.values())
    print(f"\nSUMMARY: {total_signals} signals from {total_scans} scan points "
          f"({total_signals / MONTHS_BACK:.2f}/month)")


if __name__ == "__main__":
    main()
