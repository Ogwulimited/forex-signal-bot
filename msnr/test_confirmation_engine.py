"""
Test the H1 confirmation engine.
Reuses the full pipeline up to rejection detection, then attempts
H1 confirmation on the open window.
"""
from market_data import fetch_candles
from storyline_engine import detect_daily_storyline
from zone_detector import detect_all_zones
from zone_filter import filter_zones, PIP_SCALE
from zone_classifier import classify_zones
from rejection_detector import detect_h4_rejection
from confirmation_engine import detect_h1_confirmation

PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "USDCAD", "AUDUSD"]

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

    any_rejection = False
    any_confirmation = False

    for i, setup in enumerate(classified['setups'], 1):
        setup['_storyline'] = direction
        e = setup['entry']
        o = setup['obstacle']
        pip = PIP_SCALE.get(pair, 0.0001)
        dist = abs(e['level'] - current_price) / pip

        print(f"\n  Setup {i}: {e['type']} @ {e['level']:.5f} "
              f"({dist:.1f}p from price) → {o['type']} @ {o['level']:.5f}")

        rej = detect_h4_rejection(setup, h4, pair, debug=False)

        if not rej:
            print(f"    ⏳ No rejection on last H4 candle")
            continue

        any_rejection = True
        rej['_storyline'] = direction
        print(f"    ✅ Rejection detected on last H4 close")

        conf = detect_h1_confirmation(rej, h1, pair, debug=True)

        if conf:
            any_confirmation = True
            bc = conf['break_candle']
            print(f"    ✅ CONFIRMED via {conf['method']}")
            print(f"       break candle close = {bc['close']:.5f} "
                  f"@ epoch {bc['datetime']}")
        else:
            print(f"    ⏳ Awaiting H1 confirmation in open window")

    if not any_rejection:
        print(f"\n  No rejections detected across {len(classified['setups'])} setup(s)")
