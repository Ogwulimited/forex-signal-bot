"""
Test the zone classifier across all pairs.
"""
from market_data import fetch_candles
from storyline_engine import detect_daily_storyline
from zone_detector import detect_all_zones
from zone_filter import filter_zones, PIP_SCALE
from zone_classifier import classify_zones

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
    print(f"  Filtered H4 zones: {len(zones)}")

    classified = classify_zones(direction, zones, current_price, pair, debug=True)

    if classified and classified['setups']:
        pip = PIP_SCALE.get(pair, 0.0001)
        print(f"\n  ✅ VALID SETUPS ({len(classified['setups'])}):")
        for i, s in enumerate(classified['setups'], 1):
            e = s['entry']; o = s['obstacle']
            dist = abs(e['level'] - current_price) / pip
            print(f"    {i}. {e['type']:>10} @ {e['level']:.5f} "
                  f"({dist:>5.1f}p from price) → target "
                  f"{o['type']} @ {o['level']:.5f} "
                  f"({s['room_pips']}p room)")
    else:
        print(f"\n  No valid setups (all entries filtered out)")
