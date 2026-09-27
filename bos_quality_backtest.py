"""
BOS Quality Backtest — Continuation + Reversal

Two signal modes:
  A. BOS Continuation — BOS in the direction of HTF trend
  B. Trendline-Break Reversal — trendline broken on 1H, BOS in opposite direction

Quality metrics logged per signal:
  - htf_strength (min of 4H and 1H strength)
  - rr
  - session_hour_utc
  - rejection_wick_ratio
  - atr_multiple (breakout candle move / ATR-14)
  - signal_type ('continuation' | 'reversal')

Reports: filter combinations with signals/month, WR, monthly R.
"""

import json
from collections import Counter
from datetime import datetime, timezone

from market_data import fetch_candles
from mtf_bias_engine import analyze_trend
from breakout_detector import detect_breakout
from retest_detector import detect_retest
from rejection_detector import detect_rejection
from liquidity_sweep_detector import detect_liquidity_sweep
from rr_calculator import calculate_rr
from trendline_detector import find_trendlines, price_at

PAIRS = [
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD",
    "USDCHF", "NZDUSD", "EURGBP", "EURJPY", "GBPJPY",
    "AUDJPY", "EURAUD", "EURCHF", "CADJPY", "CHFJPY",
    "XAUUSD",
]

MONTHS_BACK = 6
SCAN_EVERY_N_BARS = 5
WINDOW_5M = 100
MAX_HOLD_BARS = 576
COOLDOWN_BARS = 48
MIN_BOS_RR = 1.5
PIP_SCALE = {
    "EURUSD": 0.0001, "GBPUSD": 0.0001, "USDJPY": 0.01, "AUDUSD": 0.0001,
    "USDCAD": 0.0001, "USDCHF": 0.0001, "NZDUSD": 0.0001,
    "EURGBP": 0.0001, "EURJPY": 0.01, "GBPJPY": 0.01, "AUDJPY": 0.01,
    "EURAUD": 0.0001, "EURCHF": 0.0001, "CADJPY": 0.01, "CHFJPY": 0.01,
    "XAUUSD": 0.50,
}


# =============================================================
# DATA LOADING
# =============================================================

def load_all(pair):
    print(f"\n--- {pair} ---")
    h5 = fetch_candles(pair, interval="5min",
                       outputsize=MONTHS_BACK * 30 * 288)
    print(f"    5M: {len(h5)}")
    h1 = fetch_candles(pair, interval="1h",
                       outputsize=MONTHS_BACK * 30 * 24)
    print(f"    1H: {len(h1)}")
    h4 = fetch_candles(pair, interval="4h",
                       outputsize=MONTHS_BACK * 30 * 6)
    print(f"    4H: {len(h4)}")
    d1 = fetch_candles(pair, interval="1day",
                       outputsize=MONTHS_BACK * 30 + 100)
    print(f"    Daily: {len(d1)}")
    return h5, h1, h4, d1


# =============================================================
# HELPERS
# =============================================================

def compute_atr(candles, period=14):
    if len(candles) < period + 1:
        return None
    trs = []
    for i in range(1, period + 1):
        c = candles[-i]
        p = candles[-i - 1]
        tr = max(c['high'] - c['low'],
                 abs(c['high'] - p['close']),
                 abs(c['low'] - p['close']))
        trs.append(tr)
    return sum(trs) / len(trs)


def compute_bias(h4_slice, h1_slice):
    d4 = analyze_trend(h4_slice, lookback=20)
    d1h = analyze_trend(h1_slice, lookback=50)
    aligned = (d4['bias'] == d1h['bias'] and
               d4['bias'] in ('bullish', 'bearish'))
    return {
        'bias_4h': d4['bias'], 'bias_1h': d1h['bias'],
        'strength_4h': d4['strength'], 'strength_1h': d1h['strength'],
        'aligned': aligned,
    }


def is_trendline_broken(candles, trendline, direction):
    """Return True if trendline has been broken on the given side (recent)."""
    if not trendline:
        return False
    n = len(candles)
    lookback = min(5, n - 1)
    for i in range(n - lookback, n):
        line_y = price_at(trendline, i)
        if line_y is None or line_y <= 0:
            continue
        c = candles[i]
        if direction == 'up' and c['close'] > line_y:
            return True
        if direction == 'down' and c['close'] < line_y:
            return True
    return False


# =============================================================
# CONTINUATION PIPELINE (existing BOS)
# =============================================================

def run_continuation(candles_5m, bias_data):
    if not bias_data['aligned']:
        return None
    direction = 'buy' if bias_data['bias_4h'] == 'bullish' else 'sell'

    breakout = detect_breakout(candles_5m, direction,
                                breakout_window=10, min_bars_after_swing=3,
                                debug=False, force_breakout=False)
    if not breakout:
        return None
    retest = detect_retest(candles_5m, breakout, direction,
                            tolerance_ratio=0.0003, max_retest_bars=10,
                            debug=False)
    if not retest:
        return None
    rejection = detect_rejection(candles_5m, direction, retest=retest,
                                   breakout=breakout, debug=False)
    if not rejection:
        return None
    sweep = detect_liquidity_sweep(candles_5m, direction,
                                     breakout=breakout, retest=retest,
                                     lookback=20, debug=False,
                                     force_sweep=False)
    if not sweep:
        return None
    trade = calculate_rr(candles_5m, direction, rejection, sweep,
                          min_rr=MIN_BOS_RR, debug=False)
    if not trade:
        return None

    return {
        'signal_type': 'continuation',
        'direction': direction,
        'entry': trade['entry'], 'sl': trade['sl'],
        'tp': trade['tp'], 'rr': trade['rr'],
        'rejection_wick': rejection.get('wick_ratio', 0.0),
        'breakout_candle': breakout['break_candle'],
        'breakout_level': breakout['level'],
    }


# =============================================================
# REVERSAL PIPELINE (new)
# =============================================================

def run_reversal(candles_5m, candles_1h, bias_data):
    """
    Trendline break on 1H + opposite BOS on 5M.
    If HTF is bullish → trendline break down → SELL (reversal)
    If HTF is bearish → trendline break up → BUY (reversal)
    """
    if not bias_data['aligned']:
        return None

    tls = find_trendlines(candles_1h, lookback=200, debug=False)
    htf_dir = bias_data['bias_4h']

    if htf_dir == 'bullish':
        # Looking for support trendline that broke down
        tl = tls.get('support')
        if not tl or tl['slope'] >= 0:
            return None
        if not is_trendline_broken(candles_1h, tl, 'down'):
            return None
        direction = 'sell'
    else:  # bearish
        tl = tls.get('resistance')
        if not tl or tl['slope'] <= 0:
            return None
        if not is_trendline_broken(candles_1h, tl, 'up'):
            return None
        direction = 'buy'

    # BOS in the reversal direction on 5M
    breakout = detect_breakout(candles_5m, direction,
                                breakout_window=10, min_bars_after_swing=3,
                                debug=False, force_breakout=False)
    if not breakout:
        return None
    retest = detect_retest(candles_5m, breakout, direction,
                            tolerance_ratio=0.0003, max_retest_bars=10,
                            debug=False)
    if not retest:
        return None
    rejection = detect_rejection(candles_5m, direction, retest=retest,
                                   breakout=breakout, debug=False)
    if not rejection:
        return None
    sweep = detect_liquidity_sweep(candles_5m, direction,
                                     breakout=breakout, retest=retest,
                                     lookback=20, debug=False,
                                     force_sweep=False)
    if not sweep:
        return None
    trade = calculate_rr(candles_5m, direction, rejection, sweep,
                          min_rr=MIN_BOS_RR, debug=False)
    if not trade:
        return None

    return {
        'signal_type': 'reversal',
        'direction': direction,
        'entry': trade['entry'], 'sl': trade['sl'],
        'tp': trade['tp'], 'rr': trade['rr'],
        'rejection_wick': rejection.get('wick_ratio', 0.0),
        'breakout_candle': breakout['break_candle'],
        'breakout_level': breakout['level'],
    }


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
# PER-PAIR LOOP
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
        hour = datetime.fromtimestamp(t, tz=timezone.utc).hour
        if not (7 <= hour < 20):
            i += SCAN_EVERY_N_BARS
            continue

        candles_5m = h5[i - WINDOW_5M:i]
        h4_slice = [c for c in h4 if c['datetime'] < t]
        h1_slice = [c for c in h1 if c['datetime'] < t]
        d1_slice = [c for c in d1 if c['datetime'] < t]

        if len(h4_slice) < 40 or len(h1_slice) < 60 or len(d1_slice) < 50:
            i += SCAN_EVERY_N_BARS
            continue

        bias = compute_bias(h4_slice, h1_slice)
        if not bias['aligned']:
            i += SCAN_EVERY_N_BARS
            continue

        # Try continuation, then reversal
        sig = run_continuation(candles_5m, bias)
        if not sig:
            sig = run_reversal(candles_5m, h1_slice, bias)
        if not sig:
            i += SCAN_EVERY_N_BARS
            continue

        # Quality metrics
        strength_min = min(bias['strength_4h'], bias['strength_1h'])
        atr = compute_atr(candles_5m, 14)
        bc = sig['breakout_candle']
        breakout_move = abs(bc['close'] - sig['breakout_level'])
        atr_mult = breakout_move / atr if atr and atr > 0 else 0.0

        outcome = simulate(h5, i - 1, sig['direction'],
                            sig['entry'], sig['sl'], sig['tp'])

        signals.append({
            'pair': pair,
            'signal_type': sig['signal_type'],
            'direction': sig['direction'],
            'entry': sig['entry'], 'sl': sig['sl'], 'tp': sig['tp'],
            'rr': sig['rr'],
            'htf_strength': strength_min,
            'atr_mult': round(atr_mult, 2),
            'wick_ratio': round(sig['rejection_wick'], 2),
            'hour': hour,
            'outcome': outcome['outcome'],
            'exit_price': outcome['exit_price'],
            'bars_held': outcome['bars_held'],
            'timestamp': t,
        })
        last_signal_idx = i
        i += COOLDOWN_BARS

    return signals


# =============================================================
# STATS + REPORT
# =============================================================

def _stats(signals, months_back):
    if not signals:
        return {'total': 0, 'per_month': 0, 'wins': 0, 'losses': 0,
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


def report(signals, months_back):
    combos = [
        ((), 'Baseline (all signals)'),
        (('type=continuation',), 'Continuation only'),
        (('type=reversal',), 'Reversal only'),
        (('strength>=3',), 'Strength ≥ 3'),
        (('strength>=4',), 'Strength ≥ 4'),
        (('rr>=2.0',), 'RR ≥ 2.0'),
        (('rr>=2.5',), 'RR ≥ 2.5'),
        (('rr>=3.0',), 'RR ≥ 3.0'),
        (('wick>=0.6',), 'Wick ratio ≥ 0.6'),
        (('wick>=0.7',), 'Wick ratio ≥ 0.7'),
        (('atr>=0.3',), 'ATR mult ≥ 0.3'),
        (('session=8_17',), 'Session 8-17 UTC'),
        (('type=continuation', 'strength>=3', 'rr>=2.5'), 'Cont + Str≥3 + RR≥2.5'),
        (('type=continuation', 'strength>=3', 'rr>=2.5', 'wick>=0.6'),
         'Cont + Str≥3 + RR≥2.5 + Wick≥0.6'),
        (('type=continuation', 'strength>=3', 'rr>=2.5', 'session=8_17'),
         'Cont + Str≥3 + RR≥2.5 + Ses 8-17'),
        (('type=continuation', 'strength>=4', 'rr>=3.0', 'wick>=0.6', 'session=8_17'),
         'Cont + ALL strict'),
        (('type=reversal', 'strength>=3'), 'Reversal + Str≥3'),
        (('type=continuation', 'rr>=2.5', 'atr>=0.3'), 'Cont + RR≥2.5 + ATR≥0.3'),
    ]

    lines = ["| Filter | Signals | /mo | Wins | Losses | WR | Avg R | Monthly R |",
             "|--------|--------:|----:|-----:|-------:|---:|------:|----------:|"]

    for filters, label in combos:
        filtered = signals
        for f in filters:
            if f == 'type=continuation':
                filtered = [s for s in filtered if s['signal_type'] == 'continuation']
            elif f == 'type=reversal':
                filtered = [s for s in filtered if s['signal_type'] == 'reversal']
            elif f.startswith('strength>='):
                v = float(f.split('>=')[1])
                filtered = [s for s in filtered if s['htf_strength'] >= v]
            elif f.startswith('rr>='):
                v = float(f.split('>=')[1])
                filtered = [s for s in filtered if s['rr'] >= v]
            elif f.startswith('wick>='):
                v = float(f.split('>=')[1])
                filtered = [s for s in filtered if s['wick_ratio'] >= v]
            elif f.startswith('atr>='):
                v = float(f.split('>=')[1])
                filtered = [s for s in filtered if s['atr_mult'] >= v]
            elif f == 'session=8_17':
                filtered = [s for s in filtered if 8 <= s['hour'] < 17]

        st = _stats(filtered, months_back)
        lines.append(f"| {label} | {st['total']} | {st['per_month']} | "
                     f"{st['wins']} | {st['losses']} | {st['wr']}% | "
                     f"{st['avg_r']} | {st['monthly_r']}R |")

    return "\n".join(lines)


def per_pair_table(signals, months_back):
    lines = ["| Pair | Signals | WR | Monthly R |",
             "|------|--------:|---:|----------:|"]
    for pair in PAIRS:
        ps = [s for s in signals if s['pair'] == pair]
        st = _stats(ps, months_back)
        lines.append(f"| {pair} | {st['total']} | {st['wr']}% | "
                     f"{st['monthly_r']}R |")
    return "\n".join(lines)


def main():
    print("=" * 60)
    print("BOS QUALITY BACKTEST (Continuation + Reversal)")
    print("=" * 60)
    print(f"Pairs: {len(PAIRS)} | Months: {MONTHS_BACK}\n")

    all_signals = []
    for pair in PAIRS:
        try:
            h5, h1, h4, d1 = load_all(pair)
            if len(h5) < WINDOW_5M + 500 or len(d1) < 50:
                print(f"  Skipping {pair} (insufficient data)")
                continue
            sigs = run_pair(pair, h5, h1, h4, d1)
            cont = sum(1 for s in sigs if s['signal_type'] == 'continuation')
            rev = sum(1 for s in sigs if s['signal_type'] == 'reversal')
            print(f"  → {len(sigs)} signals (cont={cont}, rev={rev})")
            all_signals.extend(sigs)
        except Exception as e:
            print(f"  ERROR on {pair}: {e}")
            continue

    print("\n" + "=" * 60)
    print(f"TOTAL SIGNALS: {len(all_signals)}")
    print("=" * 60)

    combo_report = report(all_signals, MONTHS_BACK)
    print("\n" + combo_report)

    with open("bos_quality_report.md", "w") as f:
        f.write("# BOS Quality Backtest Report\n\n")
        f.write(f"Generated: {datetime.now(timezone.utc).isoformat()}  \n")
        f.write(f"History: {MONTHS_BACK} months | Pairs: {len(PAIRS)}\n\n")
        f.write("## Filter Combinations\n\n" + combo_report + "\n\n")
        f.write("## Per-Pair Results\n\n")
        f.write(per_pair_table(all_signals, MONTHS_BACK) + "\n\n")

    with open("bos_quality_signals.json", "w") as f:
        json.dump(all_signals, f, indent=2, default=str)

    print("\nWrote bos_quality_report.md + bos_quality_signals.json")


if __name__ == "__main__":
    main()
