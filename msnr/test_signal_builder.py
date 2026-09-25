"""
Test the signal builder end-to-end.
Runs the full pipeline: storyline → zones → classify → rejection →
confirmation → signal.
"""
import time
from market_data import fetch_candles
from storyline_engine import detect_daily_storyline
from zone_detector import detect_all_zones
from zone_filter import filter_zones
from zone_classifier import classify_zones
from rejection_detector import detect_h4_rejection
from confirmation_engine import detect_h1_confirmation
from signal_builder import build_signal

PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "USDCAD", "AUDUSD"]

current_epoch = int(time.time())
signals_found = 0

for pair in PAIRS:
    print(f"\n{'=' * 62}")
    print(f"{pair}")
    print('=' * 62)

    daily = fetch_candles(pair, interval="1day", outputsize=120)
    h4 = fetch_candles(pair, interval="4h", outputsize=200)
    h1 = fetch_candles(pair, interval="1h", outputsize=300)

    if not daily or not h4 or not h1:
        print(f"  Fetch failed")
        continue

    current_price = h4[-1]['close']
    print(f"  Current price: {current_price:.5f}")

    storyline = detect_daily_storyline(pair, daily, h4, debug=False)
    if not storyline:
        print(f"  ❌ No active storyline")
        continue

    direction = storyline['storyline']
    print(f"  ✅ Active storyline: {direction.upper()}")

    raw = detect_all_zones(h4, min_open_close_run=2, debug=False)
    zones = filter_zones(raw, h4, pair, debug=False)
    classified = classify_zones(direction, zones, current_price, pair, debug=False)

    if not classified or not classified['setups']:
        print(f"  No valid setups")
        continue

    print(f"  Valid setups: {len(classified['setups'])}")

    for i, setup in enumerate(classified['setups'], 1):
        setup['_storyline'] = direction

        e = setup['entry']
        print(f"\n  Setup {i}: {e['type']} @ {e['level']:.5f}")

        rej = detect_h4_rejection(setup, h4, pair, debug=False)
        if not rej:
            print(f"    ⏳ No rejection yet")
            continue

        rej['_storyline'] = direction
        print(f"    ✅ Rejection detected")

        conf = detect_h1_confirmation(rej, h1, pair, debug=False)
        if not conf:
            print(f"    ⏳ Awaiting H1 confirmation")
            continue

        print(f"    ✅ Confirmation via {conf['method']}")

        signal = build_signal(pair, direction, setup, rej, conf,
                              current_epoch, debug=True)
        if signal:
            signals_found += 1
            print(f"\n    📊 SIGNAL DETAILS:")
            print(f"       Pair: {signal['pair']}")
            print(f"       Direction: {signal['direction'].upper()}")
            print(f"       Entry: {signal['entry']}")
            print(f"       SL:    {signal['sl']}  ({signal['stop_pips']}p)")
            print(f"       TP:    {signal['tp']}  ({signal['target_pips']}p)")
            print(f"       RR:    {signal['rr']}")
            print(f"       Risk:  {signal['risk_pct']}% ({signal['risk_class']})")

print(f"\n{'=' * 62}")
print(f"Total signals generated: {signals_found}")
print('=' * 62)
