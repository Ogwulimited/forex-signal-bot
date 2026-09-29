"""
BOS Full Backtest — Correct Unified Model

Runs the BOS pipeline (bos_pipeline) across 30 pairs, 6 months.
Simulates each signal's outcome. Reports WR, monthly R, per-pair breakdown.
"""

import json
from datetime import datetime, timezone

from market_data import fetch_candles
from bos_pipeline import generate_signal


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
        h1_slice = [c for c in h1 if c['datetime'] < t]
        h4_slice = [c for c in h4 if c['datetime'] < t]

        if len(h4_slice) < 40 or len(h1_slice) < 60:
            i += SCAN_EVERY_N_BARS
            continue

        sig = generate_signal(pair, candles_5m, h1_slice, h4_slice, debug=False)
        if not sig:
            i += SCAN_EVERY_N_BARS
            continue

        outcome = simulate(h5, i - 1, sig['direction'],
                            sig['entry'], sig['sl'], sig['tp'])

        signals.append({
            'pair': pair,
            'direction': sig['direction'],
            'entry': sig['entry'], 'sl': sig['sl'], 'tp': sig['tp'],
            'rr': sig['rr'],
            'regime': sig['regime'],
            'outcome': outcome['outcome'],
            'exit_price': outcome['exit_price'],
            'bars_held': outcome['bars_held'],
            'timestamp': t,
        })
        last_signal_idx = i
        i += COOLDOWN_BARS

    return signals


def _stats(signals, months_back):
    if not signals:
        return {'total': 0, 'per_month': 0.0, 'wins': 0, 'losses': 0,
                'expired': 0, 'wr': 0.0, 'avg_r': 0.0, 'monthly_r': 0.0}
    wins = sum(1 for s in signals if s['outcome'] == 'win')
    losses = sum(1 for s in signals if s['outcome'] == 'loss')
    expired = sum(1 for s in signals if s['outcome'] == 'expired')
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
        'wins': wins, 'losses': losses, 'expired': expired,
        'wr': round(wins / total * 100, 1),
        'avg_r': round(r_sum / total, 2),
        'monthly_r': round(r_sum / months_back, 2),
    }


def main():
    print("=" * 60)
    print("BOS FULL BACKTEST — Unified Continuation + Reversal")
    print("=" * 60)
    print(f"Pairs: {len(PAIRS)} | Months: {MONTHS_BACK}\n")

    all_signals = []
    for pair in PAIRS:
        print(f"\n--- {pair} ---")
        try:
            h5 = fetch_candles(pair, interval="5min",
                               outputsize=MONTHS_BACK * 30 * 288)
            h1 = fetch_candles(pair, interval="1h",
                               outputsize=MONTHS_BACK * 30 * 24)
            h4 = fetch_candles(pair, interval="4h",
                               outputsize=MONTHS_BACK * 30 * 6)
            print(f"    5M={len(h5)} 1H={len(h1)} 4H={len(h4)}")

            if len(h5) < WINDOW_5M + 500:
                print(f"    Skipping {pair}")
                continue

            sigs = run_pair(pair, h5, h1, h4)
            print(f"  → {len(sigs)} signals")
            all_signals.extend(sigs)
        except Exception as e:
            print(f"  ERROR on {pair}: {e}")
            continue

    stats = _stats(all_signals, MONTHS_BACK)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Signals: {stats['total']} ({stats['per_month']}/month)")
    print(f"  Wins: {stats['wins']} | Losses: {stats['losses']} | Expired: {stats['expired']}")
    print(f"  Win rate: {stats['wr']}%")
    print(f"  Avg R/trade: {stats['avg_r']}")
    print(f"  Monthly R: {stats['monthly_r']}R")

    # Per-pair table
    print("\n" + "=" * 60)
    print("PER-PAIR RESULTS")
    print("=" * 60)
    print(f"{'Pair':<10} {'Signals':>8} {'Wins':>6} {'WR':>7} {'Monthly R':>11}")
    print("-" * 60)
    for pair in PAIRS:
        ps = [s for s in all_signals if s['pair'] == pair]
        st = _stats(ps, MONTHS_BACK)
        print(f"{pair:<10} {st['total']:>8} {st['wins']:>6} "
              f"{st['wr']:>6}% {st['monthly_r']:>10}R")

    # Save
    with open("bos_full_report.md", "w") as f:
        f.write("# BOS Full Backtest\n\n")
        f.write(f"Generated: {datetime.now(timezone.utc).isoformat()}  \n")
        f.write(f"Pairs: {len(PAIRS)} | Months: {MONTHS_BACK}\n\n")
        f.write(f"Signals: {stats['total']} ({stats['per_month']}/mo)\n")
        f.write(f"WR: {stats['wr']}% | Avg R: {stats['avg_r']} | "
                f"Monthly R: {stats['monthly_r']}R\n\n")
        f.write("## Per-Pair\n\n")
        f.write("| Pair | Signals | Wins | WR | Monthly R |\n")
        f.write("|------|--------:|-----:|---:|----------:|\n")
        for pair in PAIRS:
            ps = [s for s in all_signals if s['pair'] == pair]
            st = _stats(ps, MONTHS_BACK)
            f.write(f"| {pair} | {st['total']} | {st['wins']} | "
                    f"{st['wr']}% | {st['monthly_r']}R |\n")

    with open("bos_full_signals.json", "w") as f:
        json.dump(all_signals, f, indent=2, default=str)

    print("\nWrote bos_full_report.md + bos_full_signals.json")


if __name__ == "__main__":
    main()
