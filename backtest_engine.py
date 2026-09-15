"""
Backtest Engine - Funnel + Expectancy Diagnostic

Walks historical 5M candles pair-by-pair, reconstructs the live pipeline
at each scan point, counts funnel rejections, and simulates each signal
forward to TP/SL to measure win rate and expectancy.

Configurable SWEEP_MODE:
  - "strict"   : current production sweep (default)
  - "adaptive" : middle-ground sweep (build separately)
  - "force"    : ignore sweep stage entirely (for win-rate baseline)

Outputs:
  - backtest_report.md
  - backtest_funnel.json
  - backtest_trades.json
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
SCAN_EVERY_N_BARS = 5
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

# Trade simulation
MAX_HOLD_BARS = 576        # 48 hours of 5M candles
COOLDOWN_BARS = 48         # ~4h anti-spam, matches production

# Sweep mode: "strict" | "adaptive" | "force"
SWEEP_MODE = "strict"


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
# BIAS
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


# =============================================================
# PIPELINE (returns stage + signal dict)
# =============================================================

def run_pipeline(pair, candles_5m, bias_data, current_epoch):
    """
    Returns (stage, signal_dict_or_None).
    stage: one of bias_not_aligned / session / chop / breakout /
           retest / rejection / sweep / rr / signal
    """
    if not bias_data["aligned"]:
        return "bias_not_aligned", None

    direction = "buy" if bias_data["bias_4h"] == "bullish" else "sell"

    hour_utc = datetime.fromtimestamp(current_epoch, tz=timezone.utc).hour
    if not (7 <= hour_utc < 20):
        return "session", None

    if is_choppy(candles_5m, lookback=CHOP_LOOKBACK, min_range_ratio=CHOP_MIN_RANGE_RATIO):
        return "chop", None

    breakout = detect_breakout(
        candles_5m, direction,
        breakout_window=BREAKOUT_WINDOW,
        min_bars_after_swing=MIN_BARS_AFTER_SWING,
        debug=False, force_breakout=False,
    )
    if not breakout:
        return "breakout", None

    retest = detect_retest(
        candles_5m, breakout, direction,
        tolerance_ratio=RETEST_TOLERANCE_RATIO,
        max_retest_bars=RETEST_MAX_BARS,
        debug=False,
    )
    if not retest:
        return "retest", None

    rejection = detect_rejection(
        candles_5m, direction, retest=retest, breakout=breakout, debug=False,
    )
    if not rejection:
        return "rejection", None

    if SWEEP_MODE == "force":
        sweep = {"forced": True, "mode": "force", "level": retest["candle"]["close"]}
    else:
        sweep = detect_liquidity_sweep(
            candles_5m, direction,
            breakout=breakout, retest=retest,
            lookback=20, debug=False, force_sweep=False,
        )
        if not sweep:
            return "sweep", None

    trade = calculate_rr(
        candles_5m, direction, rejection, sweep, min_rr=RR_MIN, debug=False,
    )
    if not trade:
        return "rr", None

    return "signal", {
        "direction": direction,
        "entry": trade["entry"],
        "sl": trade["sl"],
        "tp": trade["tp"],
        "rr": trade["rr"],
        "epoch": current_epoch,
    }


# =============================================================
# TRADE SIMULATION
# =============================================================

def simulate_trade(candles_5m, entry_idx, direction, entry, sl, tp):
    """
    Walk forward from entry_idx+1 until TP or SL is hit, or MAX_HOLD_BARS reached.
    Conservative: if a single candle touches both TP and SL, count as LOSS.
    Returns dict with outcome, bars_held, exit_price, exit_idx, ambiguous.
    """
    start = entry_idx + 1
    end = min(len(candles_5m), start + MAX_HOLD_BARS)

    for i in range(start, end):
        c = candles_5m[i]
        high, low = c["high"], c["low"]

        if direction == "buy":
            tp_hit = high >= tp
            sl_hit = low <= sl
        else:
            tp_hit = low <= tp
            sl_hit = high >= sl

        if tp_hit and sl_hit:
            return {"outcome": "loss", "bars_held": i - entry_idx,
                    "exit_price": sl, "exit_idx": i, "ambiguous": True}
        if sl_hit:
            return {"outcome": "loss", "bars_held": i - entry_idx,
                    "exit_price": sl, "exit_idx": i, "ambiguous": False}
        if tp_hit:
            return {"outcome": "win", "bars_held": i - entry_idx,
                    "exit_price": tp, "exit_idx": i, "ambiguous": False}

    last = candles_5m[end - 1]
    return {"outcome": "expired", "bars_held": end - entry_idx,
            "exit_price": last["close"], "exit_idx": end - 1, "ambiguous": False}


# =============================================================
# BACKTEST ONE PAIR
# =============================================================

def backtest_pair(pair, data_5m, data_4h, data_1h, verbose=True):
    funnel = Counter()
    for s in ["bias_not_aligned", "session", "chop", "breakout",
              "retest", "rejection", "sweep", "rr", "signal"]:
        funnel[s] = 0

    trade_outcomes = []

    if len(data_5m) < WINDOW_5M + 1:
        return funnel, trade_outcomes

    epochs_4h = [c["datetime"] for c in data_4h]
    epochs_1h = [c["datetime"] for c in data_1h]

    idx_4h = 0
    idx_1h = 0
    scan_points = 0

    i = WINDOW_5M
    while i < len(data_5m):
        t = data_5m[i]["datetime"]

        while idx_4h < len(epochs_4h) and epochs_4h[idx_4h] <= t:
            idx_4h += 1
        while idx_1h < len(epochs_1h) and epochs_1h[idx_1h] <= t:
            idx_1h += 1

        if idx_4h < WINDOW_4H or idx_1h < WINDOW_1H:
            i += SCAN_EVERY_N_BARS
            continue

        candles_5m = data_5m[i - WINDOW_5M:i]
        candles_4h = data_4h[idx_4h - WINDOW_4H:idx_4h]
        candles_1h = data_1h[idx_1h - WINDOW_1H:idx_1h]

        bias_data = compute_bias(pair, candles_4h, candles_1h)
        stage, signal = run_pipeline(pair, candles_5m, bias_data, t)
        funnel[stage] += 1
        scan_points += 1

        if stage == "signal" and signal:
            outcome = simulate_trade(
                data_5m, i - 1, signal["direction"],
                signal["entry"], signal["sl"], signal["tp"],
            )
            trade_outcomes.append({
                "pair": pair,
                "epoch": t,
                "direction": signal["direction"],
                "entry": signal["entry"],
                "sl": signal["sl"],
                "tp": signal["tp"],
                "rr": signal["rr"],
                "outcome": outcome["outcome"],
                "bars_held": outcome["bars_held"],
                "exit_price": outcome["exit_price"],
                "ambiguous": outcome["ambiguous"],
            })
            i += COOLDOWN_BARS
            continue

        i += SCAN_EVERY_N_BARS

    if verbose:
        print(f"    Scan points: {scan_points}  |  Signals: {len(trade_outcomes)}")

    return funnel, trade_outcomes


# =============================================================
# REPORT
# =============================================================

def compute_expectancy_stats(trades):
    if not trades:
        return {
            "total": 0, "wins": 0, "losses": 0, "expired": 0,
            "win_rate": 0.0, "avg_r": 0.0, "total_r": 0.0,
            "avg_bars_held": 0.0, "ambiguous": 0,
        }
    wins = [t for t in trades if t["outcome"] == "win"]
    losses = [t for t in trades if t["outcome"] == "loss"]
    expired = [t for t in trades if t["outcome"] == "expired"]

    # R for wins = t['rr'] (full TP), R for losses = -1, R for expired = partial
    r_sum = 0.0
    for t in trades:
        if t["outcome"] == "win":
            r_sum += t["rr"]
        elif t["outcome"] == "loss":
            r_sum -= 1.0
        else:  # expired: use actual exit vs entry, in units of risk
            risk = abs(t["entry"] - t["sl"])
            if risk > 0:
                move = (t["exit_price"] - t["entry"]) if t["direction"] == "buy" \
                       else (t["entry"] - t["exit_price"])
                r_sum += move / risk

    total = len(trades)
    return {
        "total": total,
        "wins": len(wins),
        "losses": len(losses),
        "expired": len(expired),
        "win_rate": round(len(wins) / total * 100, 1) if total else 0.0,
        "avg_r": round(r_sum / total, 2) if total else 0.0,
        "total_r": round(r_sum, 2),
        "avg_bars_held": round(sum(t["bars_held"] for t in trades) / total, 0) if total else 0,
        "ambiguous": sum(1 for t in trades if t["ambiguous"]),
    }


def format_report(all_funnels, all_trades, months_back):
    lines = []
    lines.append("# Backtest Report — Funnel + Expectancy\n")
    lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}  ")
    lines.append(f"History window: last {months_back} months  ")
    lines.append(f"Pairs tested: {len(all_funnels)}  ")
    lines.append(f"Scan cadence: every {SCAN_EVERY_N_BARS}th 5M candle "
                 f"(~every {SCAN_EVERY_N_BARS*5} min)  ")
    lines.append(f"Sweep mode: **{SWEEP_MODE}**  ")
    lines.append(f"Cooldown between signals: {COOLDOWN_BARS} bars "
                 f"(~{COOLDOWN_BARS*5/60:.1f}h)\n")

    # ---- Funnel ----
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

    total_scan = sum(sum(f.values()) for f in all_funnels.values())

    lines.append("## Aggregate Funnel\n")
    lines.append("| Stage | Count | % of scan points |")
    lines.append("|-------|------:|-----------------:|")
    for key, label in stages:
        cnt = sum(f.get(key, 0) for f in all_funnels.values())
        pct = (cnt / total_scan * 100) if total_scan else 0
        lines.append(f"| {label} | {cnt} | {pct:.2f}% |")
    lines.append(f"| **Total scan points** | **{total_scan}** | 100% |\n")

    # ---- Expectancy ----
    all_outcomes = []
    for pair, trades in all_trades.items():
        all_outcomes.extend(trades)

    stats = compute_expectancy_stats(all_outcomes)
    per_month = stats["total"] / months_back if months_back else 0

    lines.append("## Expectancy Summary\n")
    lines.append(f"- Total signals: **{stats['total']}**")
    lines.append(f"- Signals per month: **{per_month:.2f}** across {len(all_funnels)} pairs")
    lines.append(f"- Wins: **{stats['wins']}**  |  Losses: **{stats['losses']}**  |  Expired: **{stats['expired']}**")
    lines.append(f"- Win rate: **{stats['win_rate']}%**")
    lines.append(f"- Average R per trade: **{stats['avg_r']}R**")
    lines.append(f"- Total R over {months_back} months: **{stats['total_r']}R**")
    lines.append(f"- Average hold time: **{stats['avg_bars_held']} bars** "
                 f"(~{stats['avg_bars_held']*5/60:.1f}h)")
    if stats["ambiguous"]:
        lines.append(f"- Ambiguous (TP+SL in same candle, counted as LOSS): **{stats['ambiguous']}**")
    lines.append("")

    # Monthly R projection
    if months_back > 0:
        lines.append(f"**Monthly expectancy (R): {stats['total_r'] / months_back:.2f}R**\n")

    # ---- Per-Pair ----
    lines.append("## Per-Pair Results\n")
    lines.append("| Pair | Signals | Wins | Losses | Win% | Total R |")
    lines.append("|------|--------:|-----:|-------:|-----:|--------:|")
    for pair in sorted(all_funnels.keys()):
        trades = all_trades.get(pair, [])
        ps = compute_expectancy_stats(trades)
        lines.append(f"| {pair} | {ps['total']} | {ps['wins']} | "
                     f"{ps['losses']} | {ps['win_rate']}% | {ps['total_r']}R |")
    lines.append("")

    # ---- Trade List ----
    if all_outcomes:
        lines.append("## All Signals (Chronological)\n")
        lines.append("| Date | Pair | Dir | Entry | SL | TP | RR | Outcome | Bars | R |")
        lines.append("|------|------|-----|------:|----:|----:|----:|---------|-----:|---:|")
        for t in sorted(all_outcomes, key=lambda x: x["epoch"]):
            d = datetime.fromtimestamp(t["epoch"], tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
            r = t["rr"] if t["outcome"] == "win" else (-1.0 if t["outcome"] == "loss" else 0.0)
            lines.append(f"| {d} | {t['pair']} | {t['direction']} | "
                         f"{t['entry']:.5f} | {t['sl']:.5f} | {t['tp']:.5f} | "
                         f"{t['rr']:.2f} | {t['outcome']} | {t['bars_held']} | {r:+.2f} |")
        lines.append("")

    # ---- Bottleneck ----
    aligned = sum(f.get("session", 0) + f.get("chop", 0) + f.get("breakout", 0) +
                  f.get("retest", 0) + f.get("rejection", 0) + f.get("sweep", 0) +
                  f.get("rr", 0) + f.get("signal", 0)
                  for f in all_funnels.values())
    if aligned:
        lines.append("## Bottleneck Analysis\n")
        lines.append(f"Aligned candidates: **{aligned}**\n")
        lines.append("| Filter | Rejections | % of candidates |")
        lines.append("|--------|-----------:|----------------:|")
        pairs_list = [("session", "Session"), ("chop", "Chop"), ("breakout", "Breakout"),
                      ("retest", "Retest"), ("rejection", "Rejection"),
                      ("sweep", "Sweep"), ("rr", "RR")]
        for k, label in pairs_list:
            cnt = sum(f.get(k, 0) for f in all_funnels.values())
            pct = (cnt / aligned * 100) if aligned else 0
            lines.append(f"| {label} | {cnt} | {pct:.1f}% |")
        lines.append("")

    return "\n".join(lines)


# =============================================================
# MAIN
# =============================================================

def main():
    print("=" * 60)
    print("BACKTEST ENGINE - FUNNEL + EXPECTANCY")
    print("=" * 60)
    print(f"Pairs: {len(PAIRS)}  |  History: {MONTHS_BACK} months  |  "
          f"Sweep mode: {SWEEP_MODE}")
    print()

    all_funnels = {}
    all_trades = {}

    for pair in PAIRS:
        print(f"\n--- {pair} ---")
        try:
            print("  Fetching 5M...")
            data_5m = fetch_history(pair, "5min", MONTHS_BACK)
            print(f"    5M candles: {len(data_5m)}")

            print("  Fetching 1H...")
            data_1h = fetch_history(pair, "1h", MONTHS_BACK)
            print(f"    1H candles: {len(data_1h)}")

            print("  Fetching 4H...")
            data_4h = fetch_history(pair, "4h", MONTHS_BACK)
            print(f"    4H candles: {len(data_4h)}")

            if len(data_5m) < WINDOW_5M + 100 or len(data_4h) < WINDOW_4H + 10:
                print(f"    Insufficient history, skipping")
                continue

            print("  Replaying pipeline...")
            funnel, trades = backtest_pair(pair, data_5m, data_4h, data_1h, verbose=True)
            all_funnels[pair] = funnel
            all_trades[pair] = trades

            del data_5m, data_4h, data_1h
        except Exception as e:
            print(f"  ERROR on {pair}: {e}")
            continue

    print("\n" + "=" * 60)
    print("Writing reports...")

    report = format_report(all_funnels, all_trades, MONTHS_BACK)
    with open("backtest_report.md", "w") as f:
        f.write(report)

    with open("backtest_funnel.json", "w") as f:
        json.dump({
            "generated": datetime.now(timezone.utc).isoformat(),
            "months_back": MONTHS_BACK,
            "sweep_mode": SWEEP_MODE,
            "pairs": list(all_funnels.keys()),
            "funnels": {p: dict(f) for p, f in all_funnels.items()},
        }, f, indent=2)

    all_outcomes = []
    for trades in all_trades.values():
        all_outcomes.extend(trades)

    with open("backtest_trades.json", "w") as f:
        json.dump(all_outcomes, f, indent=2, default=str)

    print("Wrote backtest_report.md, backtest_funnel.json, backtest_trades.json")

    stats = compute_expectancy_stats(all_outcomes)
    print(f"\nSUMMARY:")
    print(f"  Signals: {stats['total']} ({stats['total']/MONTHS_BACK:.2f}/month)")
    print(f"  Win rate: {stats['win_rate']}%")
    print(f"  Avg R: {stats['avg_r']}R")
    print(f"  Monthly R: {stats['total_r']/MONTHS_BACK:.2f}R")


if __name__ == "__main__":
    main()
