"""
BOS Staircase Backtest — RR filter ladder across 29 pairs.

Runs the BOS pipeline on the wide universe. Logs every signal.
Reports WR and monthly R at each RR threshold from 1.5 to 5.0.
"""

import json
from datetime import datetime, timezone

from market_data import fetch_candles
from mtf_bias_engine import analyze_trend
from breakout_detector import detect_breakout
from retest_detector import detect_retest
from rejection_detector import detect_rejection
from liquidity_sweep_detector import detect_liquidity_sweep
from rr_calculator import calculate_rr


PAIRS = [
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD",
    "EURJPY", "GBPJPY", "AUDJPY", "CADJPY", "CHFJPY", "NZDJPY",
    "EURGBP", "EURAUD", "EURCHF", "EURNZD", "EURCAD",
    "GBPAUD", "GBPCAD", "GBPCHF", "GBPNZD",
    "AUDCAD", "AUDCHF", "AUDNZD",
    "NZDCAD", "NZDCHF", "CADCHF",
    "XAUUSD",
]

MONTHS_BACK = 6
SCAN_EVERY_N_BARS = 5
WINDOW_5M = 100
MAX_HOLD_BARS = 576
COOLDOWN_BARS = 48

PIP_SCALE = {
    "EURUSD": 0.0001, "GBPUSD": 0.0001, "USDJPY": 0.01, "AUDUSD": 0.0001,
    "USDCAD": 0.0001, "USDCHF": 0.0001, "NZDUSD": 0.0001,
    "EURJPY": 0.01, "GBPJPY": 0.01, "AUDJPY": 0.01, "CADJPY": 0.01,
    "CHFJPY": 0.01, "NZDJPY": 0.01,
    "EURGBP": 0.0001, "EURAUD": 0.0001, "EURCHF": 0.0001,
    "EURNZD": 0.0001, "EURCAD": 0.0001,
    "GBPAUD": 0.0001, "GBPCAD": 0.0001, "GBPCHF": 0.0001, "GBPNZD": 0.0001,
    "AUDCAD": 0.0001, "AUDCHF": 0.0001, "AUDNZD": 0.0001,
    "NZDCAD": 0.0001, "NZDCHF": 0.0001, "CADCHF": 0.0001,
    "XAUUSD": 0.50,
}


def compute_bias(h4_slice, h1_slice):
    d4 = analyze_trend(h4_slice, lookback=20)
    d1h = analyze_trend(h1_slice, lookback=50)
    aligned = (d4['bias'] == d1h['bias'] and
               d4['bias'] in ('bullish', 'bearish'))
    return {'bias_4h': d4['bias'], 'bias_1h': d1h['bias'],
            'strength_4h': d4['strength'], 'strength_1h': d1h['strength'],
            'aligned': aligned}


def run_bos(candles_5m, bias):
    if not bias['aligned']:
        return None
    direction = 'buy' if bias['bias_4h'] == 'bullish' else 'sell'

    breakout = detect_breakout(candles_5m, direction,
                                breakout_window=10, min_bars_after_swing=3,
                                debug=False, force_breakout=False)
    if not breakout: return None
    retest = detect_retest(candles_5m, breakout, direction,
                            tolerance_ratio=0.0003, max_retest_bars=10,
                            debug=False)
    if not retest: return None
    rejection = detect_rejection(candles_5m, direction, retest=retest,
                                   breakout=breakout, debug=False)
    if not rejection: return None
    sweep = detect_liquidity_sweep(candles_5m, direction,
                                     breakout=breakout, retest=retest,
                                     lookback=20, debug=False,
                                     force_sweep=False)
    if not sweep: return None
    trade = calculate_rr(candles_5m, direction, rejection, sweep,
                          min_rr=1.5, debug=False)
    if not trade: return None

    return {
        'direction': direction,
        'entry': trade['entry'], 'sl': trade['sl'],
        'tp': trade['tp'], 'rr': trade['rr'],
        'wick_ratio': rejection.get('wick_ratio', 0.0),
    }


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
            return {'outcome': 'loss', 'exit_price': sl}
        if sl_hit:
            return {'outcome': 'loss', 'exit_price': sl}
        if tp_hit:
            return {'outcome': 'win', 'exit_price': tp}
    return {'outcome': 'expired', 'exit_price': h5[end - 1]['close']}


def run_pair(pair, h5, h1, h4):
    signals = []
    last_signal_idx = -COOLDOWN_BARS
    i = WINDOW_5M
    while i < len(h5) - 1:
        if i - last_signal_idx < COOLDOWN_BARS:
            i += SCAN_EVERY_N_BARS
            continue

        t = h5[i]['datetime']
        hour = datetime.fromtimestamp(t, tz=timezone.utc).hour
        if not (7 <= hour < 20):
            i += SCAN_EVERY_N_BARS
            continue

        candles_5m = h5[i - WINDOW_5M:i]
        h4_slice = [c for c in h4 if c['datetime'] < t]
        h1_slice = [c for c in h1 if c['datetime'] < t]

        if len(h4_slice) < 40 or len(h1_slice) < 60:
            i += SCAN_EVERY_N_BARS
            continue

        bias = compute_bias(h4_slice, h1_slice)
        sig = run_bos(candles_5m, bias)
        if not sig:
            i += SCAN_EVERY_N_BARS
            continue

        strength_min = min(bias['strength_4h'], bias['strength_1h'])
        outcome = simulate(h5, i - 1, sig['direction'],
                            sig['entry'], sig['sl'], sig['tp'])

        signals.append({
            'pair': pair,
            'direction': sig['direction'],
            'entry': sig['entry'], 'sl': sig['sl'], 'tp': sig['tp'],
            'rr': sig['rr'],
            'htf_strength': strength_min,
            'wick_ratio': round(sig['wick_ratio'], 2),
            'hour': hour,
            'outcome': outcome['outcome'],
            'exit_price': outcome['exit_price'],
            'timestamp': t,
        })
        last_signal_idx = i
        i += COOLDOWN_BARS

    return signals


def _stats(signals, months_back):
    if not signals:
        return {'total': 0, 'per_month': 0.0, 'wins': 0, 'losses': 0,
                'wr': 0.0, 'avg_r': 0.0, 'monthly_r': 0.0}
    wins = sum(1 for s in signals if s['outcome'] == 'win')
    losses = sum(1 for s in signals if s['outcome'] == 'loss')
    r_sum = 0.0
    for s in signals:
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
    total = len(signals)
    return {
        'total': total, 'per_month': round(total / months_back, 1),
        'wins': wins, 'losses': losses,
        'wr': round(wins / total * 100, 1),
        'avg_r': round(r_sum / total, 2),
        'monthly_r': round(r_sum / months_back, 2),
    }


def staircase(signals, months_back):
    lines = ["| Min RR | Signals | /mo | Wins | Losses | WR | Monthly R |",
             "|-------:|--------:|----:|-----:|-------:|---:|----------:|"]
    for rr in [1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]:
        filt = [s for s in signals if s['rr'] >= rr]
        st = _stats(filt, months_back)
        lines.append(f"| ≥ {rr} | {st['total']} | {st['per_month']} | "
                     f"{st['wins']} | {st['losses']} | {st['wr']}% | "
                     f"{st['monthly_r']}R |")
    return "\n".join(lines)


def main():
    print("=" * 60)
    print(f"BOS STAIRCASE — {len(PAIRS)} pairs, {MONTHS_BACK} months")
    print("=" * 60)

    all_signals = []
    for pair in PAIRS:
        try:
            h5 = fetch_candles(pair, interval="5min",
                               outputsize=MONTHS_BACK * 30 * 288)
            h1 = fetch_candles(pair, interval="1h",
                               outputsize=MONTHS_BACK * 30 * 24)
            h4 = fetch_candles(pair, interval="4h",
                               outputsize=MONTHS_BACK * 30 * 6)
            if len(h5) < WINDOW_5M + 500:
                print(f"  {pair}: skipped")
                continue
            sigs = run_pair(pair, h5, h1, h4)
            print(f"  {pair}: {len(sigs)} signals")
            all_signals.extend(sigs)
        except Exception as e:
            print(f"  ERROR on {pair}: {e}")
            continue

    print("\n" + "=" * 60)
    print(f"TOTAL: {len(all_signals)} signals")
    print("=" * 60)

    tbl = staircase(all_signals, MONTHS_BACK)
    print("\n" + tbl)

    with open("bos_staircase_report.md", "w") as f:
        f.write("# BOS Staircase Backtest\n\n")
        f.write(f"Pairs: {len(PAIRS)} | Months: {MONTHS_BACK}\n\n")
        f.write(tbl + "\n\n")
        f.write("## Per-Pair (RR ≥ 2.5)\n\n")
        f.write("| Pair | Signals | Wins | WR | Monthly R |\n")
        f.write("|------|--------:|-----:|---:|----------:|\n")
        for pair in PAIRS:
            ps = [s for s in all_signals if s['pair'] == pair and s['rr'] >= 2.5]
            st = _stats(ps, MONTHS_BACK)
            f.write(f"| {pair} | {st['total']} | {st['wins']} | "
                    f"{st['wr']}% | {st['monthly_r']}R |\n")

    with open("bos_staircase_signals.json", "w") as f:
        json.dump(all_signals, f, indent=2, default=str)

    print("\nWrote bos_staircase_report.md + bos_staircase_signals.json")


if __name__ == "__main__":
    main()
