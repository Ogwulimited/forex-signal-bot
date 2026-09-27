"""
Hybrid Backtest — BOS Signals + MSNR Quality Gate

Runs the BOS pipeline on 5M candles across 16 pairs. For each BOS signal,
evaluates three MSNR-derived filters:

  F1 — Daily storyline alignment (bullish/bearish matches BOS direction)
  F2 — H4 zone confluence (BOS entry price near a validated MSNR H4 zone)
  F3 — H1 confirmation (recent H1 QM in trade direction, within 12 candles)

Simulates each trade's outcome regardless of filters, then reports
statistics for all 8 filter combinations at the end.
"""

import os
import sys
import json
from collections import Counter
from datetime import datetime, timezone

# Add msnr/ to path so we can import its modules
# NOTE: use append (not insert) so root versions win for shared names
# like rejection_detector and market_data.
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(_HERE, 'msnr'))

from market_data import fetch_candles
from mtf_bias_engine import analyze_trend
from breakout_detector import detect_breakout
from retest_detector import detect_retest
from rejection_detector import detect_rejection
from liquidity_sweep_detector import detect_liquidity_sweep
from rr_calculator import calculate_rr

from storyline_engine import detect_daily_storyline
from zone_detector import detect_all_zones
from zone_filter import filter_zones, PIP_SCALE
from zone_classifier import classify_zones
from qm_detector import detect_qm


# =============================================================
# CONFIG
# =============================================================

PAIRS = [
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD",
    "USDCHF", "NZDUSD", "EURGBP", "EURJPY", "GBPJPY",
    "AUDJPY", "EURAUD", "EURCHF", "CADJPY", "CHFJPY",
    "XAUUSD",
]

MONTHS_BACK = 6
SCAN_EVERY_N_BARS = 5
WINDOW_5M = 100
MAX_HOLD_BARS = 576         # 48h
COOLDOWN_BARS = 48          # 4h between signals per pair
MIN_BOS_RR = 1.5


# =============================================================
# DATA LOADING
# =============================================================

def load_all(pair):
    print(f"\n--- {pair} ---")
    print("  Fetching 5M...")
    h5 = fetch_candles(pair, interval="5min",
                       outputsize=MONTHS_BACK * 30 * 288 + 200)
    print(f"    5M: {len(h5)}")

    print("  Fetching 1H...")
    h1 = fetch_candles(pair, interval="1h",
                       outputsize=MONTHS_BACK * 30 * 24 + 200)
    print(f"    1H: {len(h1)}")

    print("  Fetching 4H...")
    h4 = fetch_candles(pair, interval="4h",
                       outputsize=MONTHS_BACK * 30 * 6 + 100)
    print(f"    4H: {len(h4)}")

    print("  Fetching Daily...")
    d1 = fetch_candles(pair, interval="1day",
                       outputsize=MONTHS_BACK * 30 + 200)
    print(f"    Daily: {len(d1)}")

    return h5, h1, h4, d1


# =============================================================
# BOS BIAS + PIPELINE (sliced, no lookahead)
# =============================================================

def compute_bias(h4_slice, h1_slice):
    d4 = analyze_trend(h4_slice, lookback=20)
    d1h = analyze_trend(h1_slice, lookback=50)
    aligned = (d4['bias'] == d1h['bias'] and
               d4['bias'] in ('bullish', 'bearish'))
    return {
        'bias_4h': d4['bias'],
        'bias_1h': d1h['bias'],
        'aligned': aligned,
    }


def run_bos_pipeline(candles_5m, bias_data):
    """Returns a BOS signal dict or None."""
    if not bias_data or not bias_data['aligned']:
        return None

    direction = 'buy' if bias_data['bias_4h'] == 'bullish' else 'sell'

    # Session filter: London + NY only (7-20 UTC)
    hour = datetime.fromtimestamp(candles_5m[-1]['datetime'],
                                   tz=timezone.utc).hour
    if not (7 <= hour < 20):
        return None

    breakout = detect_breakout(
        candles_5m, direction,
        breakout_window=10, min_bars_after_swing=3,
        debug=False, force_breakout=False,
    )
    if not breakout:
        return None

    retest = detect_retest(
        candles_5m, breakout, direction,
        tolerance_ratio=0.0003, max_retest_bars=10, debug=False,
    )
    if not retest:
        return None

    rejection = detect_rejection(
        candles_5m, direction, retest=retest,
        breakout=breakout, debug=False,
    )
    if not rejection:
        return None

    sweep = detect_liquidity_sweep(
        candles_5m, direction,
        breakout=breakout, retest=retest,
        lookback=20, debug=False, force_sweep=False,
        sweep_mode='adaptive',
    )
    if not sweep:
        return None

    trade = calculate_rr(
        candles_5m, direction, rejection, sweep,
        min_rr=MIN_BOS_RR, debug=False,
    )
    if not trade:
        return None

    return {
        'direction': direction,
        'entry': trade['entry'],
        'sl': trade['sl'],
        'tp': trade['tp'],
        'rr': trade['rr'],
    }


# =============================================================
# QUALITY GATE — 3 MSNR FILTERS
# =============================================================

def evaluate_gate(pair, direction, d1_slice, h4_slice, h1_slice):
    """
    Evaluate three MSNR filters on a BOS signal.
    direction: 'buy' or 'sell'
    Returns: {'f1': bool, 'f2': bool, 'f3': bool}
    """
    msnr_dir = 'bullish' if direction == 'buy' else 'bearish'
    result = {'f1': False, 'f2': False, 'f3': False}

    # F1 — Daily storyline alignment
    try:
        storyline = detect_daily_storyline(pair, d1_slice, h4_slice, debug=False)
        if storyline and storyline['storyline'] == msnr_dir:
            result['f1'] = True
    except Exception:
        pass

    # F2 — H4 zone confluence (entry price near a valid MSNR H4 zone)
    try:
        current_price = h4_slice[-1]['close']
        raw = detect_all_zones(h4_slice, min_open_close_run=2, debug=False)
        zones = filter_zones(raw, h4_slice, pair, debug=False)
        classified = classify_zones(msnr_dir, zones, current_price, pair,
                                    debug=False)
        if classified and classified['setups']:
            pip = PIP_SCALE.get(pair, 0.0001)
            for setup in classified['setups']:
                dist = abs(setup['entry']['level'] - current_price) / pip
                if dist <= 50:
                    result['f2'] = True
                    break
    except Exception:
        pass

    # F3 — H1 confirmation (recent QM in trade direction)
    try:
        qm = detect_qm(h1_slice, msnr_dir, pair=pair, debug=False)
        if qm and qm['candles_since_break'] <= 12:
            result['f3'] = True
    except Exception:
        pass

    return result


# =============================================================
# TRADE SIMULATION
# =============================================================

def simulate(h5, entry_idx, direction, entry, sl, tp):
    start = entry_idx + 1
    end = min(len(h5), start + MAX_HOLD_BARS)

    for i in range(start, end):
        c = h5[i]
        if direction == 'buy':
            tp_hit = c['high'] >= tp
            sl_hit = c['low'] <= sl
        else:
            tp_hit = c['low'] <= tp
            sl_hit = c['high'] >= sl

        if tp_hit and sl_hit:
            return {'outcome': 'loss', 'exit_price': sl,
                    'bars_held': i - entry_idx}
        if sl_hit:
            return {'outcome': 'loss', 'exit_price': sl,
                    'bars_held': i - entry_idx}
        if tp_hit:
            return {'outcome': 'win', 'exit_price': tp,
                    'bars_held': i - entry_idx}

    last = h5[end - 1]
    return {'outcome': 'expired', 'exit_price': last['close'],
            'bars_held': end - entry_idx - 1}


# =============================================================
# BACKTEST ONE PAIR
# =============================================================

def run_pair(pair, h5, h1, h4, d1):
    signals = []
    last_signal_idx = -COOLDOWN_BARS

    i = WINDOW_5M
    while i < len(h5) - 1:
        if i - last_signal_idx < COOLDOWN_BARS:
            i += SCAN_EVERY_N_BARS
            continue

        t = h5[i]['datetime']
        candles_5m = h5[i - WINDOW_5M:i]

        # Sliced higher-timeframe candles (no lookahead)
        h4_slice = [c for c in h4 if c['datetime'] < t]
        h1_slice = [c for c in h1 if c['datetime'] < t]
        d1_slice = [c for c in d1 if c['datetime'] < t]

        if len(h4_slice) < 40 or len(h1_slice) < 60 or len(d1_slice) < 50:
            i += SCAN_EVERY_N_BARS
            continue

        bias = compute_bias(h4_slice, h1_slice)
        bos = run_bos_pipeline(candles_5m, bias)
        if not bos:
            i += SCAN_EVERY_N_BARS
            continue

        gate = evaluate_gate(pair, bos['direction'], d1_slice, h4_slice, h1_slice)
        outcome = simulate(h5, i - 1, bos['direction'],
                            bos['entry'], bos['sl'], bos['tp'])

        signals.append({
            'pair': pair,
            'direction': bos['direction'],
            'entry': bos['entry'],
            'sl': bos['sl'],
            'tp': bos['tp'],
            'rr': bos['rr'],
            'f1': gate['f1'],
            'f2': gate['f2'],
            'f3': gate['f3'],
            'outcome': outcome['outcome'],
            'exit_price': outcome['exit_price'],
            'bars_held': outcome['bars_held'],
            'index': i,
            'timestamp': t,
        })
        last_signal_idx = i
        i += COOLDOWN_BARS

    return signals


# =============================================================
# REPORTING
# =============================================================

def _stats(filtered, months_back):
    if not filtered:
        return {'total': 0, 'per_month': 0, 'wins': 0, 'losses': 0,
                'expired': 0, 'wr': 0.0, 'avg_r': 0.0, 'monthly_r': 0.0}
    wins = sum(1 for s in filtered if s['outcome'] == 'win')
    losses = sum(1 for s in filtered if s['outcome'] == 'loss')
    expired = sum(1 for s in filtered if s['outcome'] == 'expired')
    r_sum = 0.0
    for s in filtered:
        if s['outcome'] == 'win':
            r_sum += s['rr']
        elif s['outcome'] == 'loss':
            r_sum -= 1.0
        else:
            risk = abs(s['entry'] - s['sl'])
            if risk > 0:
                pip = PIP_SCALE.get(s['pair'], 0.0001)
                risk_pips = risk / pip
                move = ((s['exit_price'] - s['entry']) if s['direction'] == 'buy'
                        else (s['entry'] - s['exit_price']))
                r_sum += (move / pip) / risk_pips
    total = len(filtered)
    return {
        'total': total,
        'per_month': round(total / months_back, 1),
        'wins': wins, 'losses': losses, 'expired': expired,
        'wr': round(wins / total * 100, 1),
        'avg_r': round(r_sum / total, 2),
        'monthly_r': round(r_sum / months_back, 2),
    }


def report_combos(all_signals, months_back):
    combos = [
        ((), 'BOS only (baseline)'),
        (('f1',), 'BOS + F1 (storyline)'),
        (('f2',), 'BOS + F2 (H4 zone)'),
        (('f3',), 'BOS + F3 (H1 QM)'),
        (('f1', 'f2'), 'BOS + F1+F2'),
        (('f1', 'f3'), 'BOS + F1+F3'),
        (('f2', 'f3'), 'BOS + F2+F3'),
        (('f1', 'f2', 'f3'), 'BOS + F1+F2+F3'),
    ]
    lines = ["| Filter | Signals | /mo | Wins | Losses | WR | Avg R | Monthly R |",
             "|--------|--------:|----:|-----:|-------:|---:|------:|----------:|"]
    for filters, label in combos:
        if not filters:
            filtered = all_signals
        else:
            filtered = [s for s in all_signals
                        if all(s.get(f, False) for f in filters)]
        st = _stats(filtered, months_back)
        lines.append(f"| {label} | {st['total']} | {st['per_month']} | "
                     f"{st['wins']} | {st['losses']} | {st['wr']}% | "
                     f"{st['avg_r']} | {st['monthly_r']}R |")
    return "\n".join(lines)


def per_pair_table(all_signals, months_back, filters):
    lines = ["| Pair | Signals | WR | Monthly R |",
             "|------|--------:|---:|----------:|"]
    for pair in PAIRS:
        pair_signals = [s for s in all_signals if s['pair'] == pair]
        if filters:
            pair_signals = [s for s in pair_signals
                            if all(s.get(f, False) for f in filters)]
        st = _stats(pair_signals, months_back)
        lines.append(f"| {pair} | {st['total']} | {st['wr']}% | "
                     f"{st['monthly_r']}R |")
    return "\n".join(lines)


# =============================================================
# MAIN
# =============================================================

def main():
    print("=" * 60)
    print("HYBRID BACKTEST — BOS + MSNR Quality Gate")
    print("=" * 60)
    print(f"Pairs: {len(PAIRS)} | Months: {MONTHS_BACK}\n")

    all_signals = []

    for pair in PAIRS:
        try:
            h5, h1, h4, d1 = load_all(pair)
            if len(h5) < WINDOW_5M + 500 or len(d1) < 50:
                print(f"  Insufficient data — skipping {pair}")
                continue

            signals = run_pair(pair, h5, h1, h4, d1)
            print(f"  → {len(signals)} BOS signals")
            all_signals.extend(signals)

        except Exception as e:
            print(f"  ERROR on {pair}: {e}")
            continue

    print("\n" + "=" * 60)
    print(f"TOTAL BOS SIGNALS: {len(all_signals)}")
    print("=" * 60)

    combo_report = report_combos(all_signals, MONTHS_BACK)
    print("\n" + combo_report)

    # Full report
    with open("hybrid_backtest_report.md", "w") as f:
        f.write("# Hybrid BOS + MSNR Quality Gate — Backtest Report\n\n")
        f.write(f"Generated: {datetime.now(timezone.utc).isoformat()}  \n")
        f.write(f"History: {MONTHS_BACK} months | Pairs: {len(PAIRS)}\n\n")

        f.write("## Filter Combinations\n\n")
        f.write(combo_report + "\n\n")

        f.write("## Per-Pair (BOS only)\n\n")
        f.write(per_pair_table(all_signals, MONTHS_BACK, filters=()) + "\n\n")

        f.write("## Per-Pair (BOS + F1 + F2 + F3)\n\n")
        f.write(per_pair_table(all_signals, MONTHS_BACK,
                                filters=('f1', 'f2', 'f3')) + "\n\n")

        f.write("## All Signals (Chronological)\n\n")
        f.write("| Date | Pair | Dir | Entry | RR | Outcome | F1 | F2 | F3 |\n")
        f.write("|------|------|-----|------:|---:|---------|:--:|:--:|:--:|\n")
        for s in sorted(all_signals, key=lambda x: x['timestamp']):
            d = datetime.fromtimestamp(s['timestamp'],
                                        tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
            f.write(f"| {d} | {s['pair']} | {s['direction']} | "
                    f"{s['entry']:.5f} | {s['rr']:.2f} | {s['outcome']} | "
                    f"{'✅' if s['f1'] else '·'} | "
                    f"{'✅' if s['f2'] else '·'} | "
                    f"{'✅' if s['f3'] else '·'} |\n")

    with open("hybrid_backtest_signals.json", "w") as f:
        json.dump(all_signals, f, indent=2, default=str)

    print("\nWrote hybrid_backtest_report.md + hybrid_backtest_signals.json")


if __name__ == "__main__":
    main()
