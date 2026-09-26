"""
MSNR Backtest Engine v2

Changes:
  - FIXED: h1_slice now passes full history to confirmation engine,
    which slices the window internally. Previous version truncated
    h1 to only candles before the window opened, so confirmation
    could never fire.
  - Added stage counters (storyline_active, setups_found,
    rejections_found, confirmations_found, signals_taken) for
    diagnosis.
"""

import json
import time
from collections import Counter
from datetime import datetime, timezone

from market_data import fetch_candles
from storyline_engine import detect_daily_storyline
from zone_detector import detect_all_zones
from zone_filter import filter_zones, PIP_SCALE
from zone_classifier import classify_zones
from rejection_detector import detect_h4_rejection
from confirmation_engine import detect_h1_confirmation
from signal_builder import build_signal


# =============================================================
# CONFIG
# =============================================================

PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "USDCAD", "AUDUSD"]
MONTHS_BACK = 6
H4_SECONDS = 4 * 3600
DAY_SECONDS = 86400
COOLDOWN_SECONDS = 48 * 3600
MAX_HOLD_H4 = 12
WARMUP_H4 = 60
WARMUP_DAILY = 50


# =============================================================
# TRADE SIMULATION
# =============================================================

def simulate_trade(h4_candles, entry_idx, signal):
    direction = signal['direction']
    sl = signal['sl']
    tp = signal['tp']

    start = entry_idx + 1
    end = min(len(h4_candles), start + MAX_HOLD_H4)

    for i in range(start, end):
        c = h4_candles[i]
        high, low = c['high'], c['low']

        if direction == 'sell':
            tp_hit = low <= tp
            sl_hit = high >= sl
        else:
            tp_hit = high >= tp
            sl_hit = low <= sl

        if tp_hit and sl_hit:
            return {'outcome': 'loss', 'exit_price': sl, 'exit_idx': i,
                    'bars_held': i - entry_idx, 'ambiguous': True}
        if sl_hit:
            return {'outcome': 'loss', 'exit_price': sl, 'exit_idx': i,
                    'bars_held': i - entry_idx, 'ambiguous': False}
        if tp_hit:
            return {'outcome': 'win', 'exit_price': tp, 'exit_idx': i,
                    'bars_held': i - entry_idx, 'ambiguous': False}

    last = h4_candles[end - 1]
    return {'outcome': 'expired', 'exit_price': last['close'],
            'exit_idx': end - 1, 'bars_held': end - entry_idx - 1,
            'ambiguous': False}


# =============================================================
# BACKTEST ONE PAIR
# =============================================================

def run_pair(pair, h4_candles, h1_candles, daily_candles, counters, verbose=True):
    signals = []
    last_signal_epoch = -COOLDOWN_SECONDS

    daily_cache_key = None
    daily_cache = None

    i = WARMUP_H4
    while i < len(h4_candles) - 1:
        current_h4 = h4_candles[i]
        t = current_h4['datetime']
        day_open = t - (t % DAY_SECONDS)

        if day_open != daily_cache_key:
            daily_slice = [c for c in daily_candles
                           if c['datetime'] < day_open]
            if len(daily_slice) < WARMUP_DAILY:
                i += 1
                continue

            h4_slice_for_daily = h4_candles[:i + 1]
            storyline = detect_daily_storyline(
                pair, daily_slice, h4_slice_for_daily, debug=False
            )
            daily_cache_key = day_open
            daily_cache = {'storyline': storyline}

        storyline = daily_cache['storyline']
        if not storyline:
            i += 1
            continue

        counters['storyline_active'] += 1
        direction = storyline['storyline']
        current_price = current_h4['close']

        h4_slice = h4_candles[:i + 1]
        raw_zones = detect_all_zones(h4_slice, min_open_close_run=2, debug=False)
        filtered_zones = filter_zones(raw_zones, h4_slice, pair, debug=False)

        classified = classify_zones(direction, filtered_zones,
                                    current_price, pair, debug=False)
        if not classified or not classified['setups']:
            i += 1
            continue

        counters['setups_found'] += len(classified['setups'])

        for setup in classified['setups']:
            setup['_storyline'] = direction

            rej = detect_h4_rejection(setup, h4_slice, pair, debug=False)
            if not rej:
                continue
            counters['rejections_found'] += 1
            rej['_storyline'] = direction

            # ★ FIX: pass FULL H1 history; confirmation engine slices window itself.
            conf = detect_h1_confirmation(rej, h1_candles, pair, debug=False)
            if not conf:
                continue
            counters['confirmations_found'] += 1

            if t - last_signal_epoch < COOLDOWN_SECONDS:
                continue

            signal = build_signal(pair, direction, setup, rej, conf, t,
                                   debug=False)
            if not signal:
                continue

            outcome = simulate_trade(h4_candles, i, signal)
            signal.update(outcome)
            signals.append(signal)
            counters['signals_taken'] += 1
            last_signal_epoch = t
            break

        i += 1

    if verbose:
        print(f"    Scan complete: {len(signals)} signals")

    return signals


# =============================================================
# REPORTING
# =============================================================

def compute_stats(signals, months_back):
    if not signals:
        return {
            'total': 0, 'wins': 0, 'losses': 0, 'expired': 0,
            'win_rate': 0.0, 'total_r': 0.0, 'avg_r': 0.0,
            'signals_per_month': 0.0, 'monthly_r': 0.0,
            'avg_hold_h': 0.0, 'avg_rr': 0.0,
        }

    wins = [s for s in signals if s['outcome'] == 'win']
    losses = [s for s in signals if s['outcome'] == 'loss']
    expired = [s for s in signals if s['outcome'] == 'expired']

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
                move = (s['exit_price'] - s['entry']) if s['direction'] == 'buy' \
                       else (s['entry'] - s['exit_price'])
                r_sum += (move / pip) / risk_pips

    total = len(signals)
    return {
        'total': total,
        'wins': len(wins),
        'losses': len(losses),
        'expired': len(expired),
        'win_rate': round(len(wins) / total * 100, 1),
        'total_r': round(r_sum, 2),
        'avg_r': round(r_sum / total, 2),
        'signals_per_month': round(total / months_back, 2),
        'monthly_r': round(r_sum / months_back, 2),
        'avg_hold_h': round(sum(s['bars_held'] for s in signals) * 4 / total, 1),
        'avg_rr': round(sum(s['rr'] for s in signals) / total, 2),
    }


def format_report(all_signals, months_back, counters):
    lines = []
    lines.append("# MSNR Backtest Report\n")
    lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}  ")
    lines.append(f"History: last {months_back} months  ")
    lines.append(f"Pairs: {len(PAIRS)}  ")
    lines.append(f"Cooldown: {COOLDOWN_SECONDS//3600}h  |  Max hold: {MAX_HOLD_H4*4}h\n")

    stats = compute_stats(all_signals, months_back)

    lines.append("## Pipeline Counters\n")
    lines.append(f"- Storyline-active scans: **{counters['storyline_active']}**")
    lines.append(f"- Setups found: **{counters['setups_found']}**")
    lines.append(f"- Rejections detected: **{counters['rejections_found']}**")
    lines.append(f"- Confirmations found: **{counters['confirmations_found']}**")
    lines.append(f"- Signals taken (post-cooldown): **{counters['signals_taken']}**\n")

    lines.append("## Expectancy Summary\n")
    lines.append(f"- Total signals: **{stats['total']}**")
    lines.append(f"- Signals/month: **{stats['signals_per_month']}**")
    lines.append(f"- Wins: **{stats['wins']}** | Losses: **{stats['losses']}** | Expired: **{stats['expired']}**")
    lines.append(f"- Win rate: **{stats['win_rate']}%**")
    lines.append(f"- Avg RR: **{stats['avg_rr']}**")
    lines.append(f"- Avg R/trade: **{stats['avg_r']}**")
    lines.append(f"- Total R over {months_back} mo: **{stats['total_r']}R**")
    lines.append(f"- **Monthly R: {stats['monthly_r']}R**")
    lines.append(f"- Avg hold: **{stats['avg_hold_h']}h**\n")

    lines.append("## Per-Pair Results\n")
    lines.append("| Pair | Signals | Wins | Losses | Win% | Total R |")
    lines.append("|------|--------:|-----:|-------:|-----:|--------:|")
    for pair in PAIRS:
        pair_signals = [s for s in all_signals if s['pair'] == pair]
        ps = compute_stats(pair_signals, months_back) if pair_signals else {
            'total': 0, 'wins': 0, 'losses': 0, 'win_rate': 0.0, 'total_r': 0.0
        }
        lines.append(f"| {pair} | {ps['total']} | {ps['wins']} | "
                     f"{ps['losses']} | {ps['win_rate']}% | {ps['total_r']}R |")
    lines.append("")

    if all_signals:
        lines.append("## Signals (Chronological)\n")
        lines.append("| Date | Pair | Dir | Entry | SL | TP | RR | Outcome | Bars |")
        lines.append("|------|------|-----|------:|----:|----:|----:|---------|-----:|")
        for s in sorted(all_signals, key=lambda x: x['timestamp']):
            d = datetime.fromtimestamp(s['timestamp'], tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
            lines.append(f"| {d} | {s['pair']} | {s['direction']} | "
                         f"{s['entry']:.5f} | {s['sl']:.5f} | {s['tp']:.5f} | "
                         f"{s['rr']:.2f} | {s['outcome']} | {s['bars_held']} |")
        lines.append("")

    return "\n".join(lines)


# =============================================================
# MAIN
# =============================================================

def main():
    print("=" * 60)
    print("MSNR BACKTEST v2")
    print("=" * 60)
    print(f"Pairs: {len(PAIRS)} | Months: {MONTHS_BACK}\n")

    all_signals = []
    counters = Counter()

    for pair in PAIRS:
        print(f"\n--- {pair} ---")
        try:
            print("  Fetching H4...")
            h4 = fetch_candles(pair, interval="4h",
                               outputsize=MONTHS_BACK * 30 * 6 + 100)
            print(f"    {len(h4)} H4 candles")

            print("  Fetching H1...")
            h1 = fetch_candles(pair, interval="1h",
                               outputsize=MONTHS_BACK * 30 * 24 + 200)
            print(f"    {len(h1)} H1 candles")

            print("  Fetching Daily...")
            daily = fetch_candles(pair, interval="1day",
                                   outputsize=MONTHS_BACK * 30 + 150)
            print(f"    {len(daily)} Daily candles")

            if len(h4) < WARMUP_H4 + 100 or len(daily) < WARMUP_DAILY + 30:
                print("    Insufficient data, skipping")
                continue

            signals = run_pair(pair, h4, h1, daily, counters, verbose=True)
            all_signals.extend(signals)

        except Exception as e:
            print(f"  ERROR on {pair}: {e}")
            continue

    print("\n" + "=" * 60)
    print("Pipeline counters:")
    print(f"  Storyline-active scans:  {counters['storyline_active']}")
    print(f"  Setups found:            {counters['setups_found']}")
    print(f"  Rejections detected:     {counters['rejections_found']}")
    print(f"  Confirmations found:     {counters['confirmations_found']}")
    print(f"  Signals taken:           {counters['signals_taken']}")
    print("=" * 60)

    print("Writing reports...")
    report = format_report(all_signals, MONTHS_BACK, counters)
    with open("backtest_report.md", "w") as f:
        f.write(report)
    with open("backtest_trades.json", "w") as f:
        json.dump(all_signals, f, indent=2, default=str)

    stats = compute_stats(all_signals, MONTHS_BACK)
    print(f"\nSUMMARY")
    print(f"  Signals: {stats['total']} ({stats['signals_per_month']}/month)")
    print(f"  Win rate: {stats['win_rate']}%")
    print(f"  Avg RR: {stats['avg_rr']}")
    print(f"  Monthly R: {stats['monthly_r']}R")
    print(f"\nWrote backtest_report.md and backtest_trades.json")


if __name__ == "__main__":
    main()
