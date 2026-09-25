"""
Test the H4 rejection detector across all pairs.
Wraps the classifier output with the storyline direction so the
rejection detector knows which way to look.
"""
from market_data import fetch_candles
from storyline_engine import detect_daily_storyline
from zone_detector import detect_all_zones
from zone_filter import filter_zones, PIP_SCALE
from zone_classifier import classify_zones
from rejection_detector import detect_h4_rejection

PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "USDCAD", "AUDUSD"]

for pair in PAIRS:
    print(f"\n{'=' * 62}")
    print(f"{pair}")
    print('=' * 62)

    daily = fetch_candles(pair, interval="1day", outputsize=120)
    h4 = fetch_candles(pair, interval="4h", outputsize=200)

    if not daily or not h4:
        print(f"  Fetch failed")
        continue

    current_price = h4[-1]['close']
    print(f"  Current price: {current_price:.5f}")

    storyline = detect_daily_storyline(pair, daily, h4, debug=False)

    if not storyline:
        print(f"  ❌ No active storyline — skipping")
        continue

    direction = storyline['storyline']
    print(f"  ✅ Active storyline: {direction.upper()}")

    raw = detect_all_zones(h4, min_open_close_run=2, debug=False)
    zones = filter_zones(raw, h4, pair, debug=False)
    classified = classify_zones(direction, zones, current_price, pair, debug=False)

    if not classified or not classified['setups']:
        print(f"  No valid setups — nothing to reject")
        continue

    print(f"  Valid setups: {len(classified['setups'])}")

    # Check each setup for rejection on the last closed H4 candle
    for i, setup in enumerate(classified['setups'], 1):
        # Attach direction so the detector knows which side to look
        setup['_storyline'] = direction

        e = setup['entry']
        o = setup['obstacle']
        pip = PIP_SCALE.get(pair, 0.0001)
        dist = abs(e['level'] - current_price) / pip

        print(f"\n  Setup {i}: {e['type']} @ {e['level']:.5f} "
              f"({dist:.1f}p from price) → {o['type']} @ {o['level']:.5f}")

        rej = detect_h4_rejection(setup, h4, pair, debug=True)

        if rej:
            print(f"  ✅ REJECTION ACTIVE — entry window open")
            print(f"     Waiting for H1 confirmation in next H4 candle")
        else:
            print(f"  ⏳ No rejection yet on last closed H4 candle")
