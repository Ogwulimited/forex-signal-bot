"""
Test the zone classifier across all pairs.
Uses the storyline engine to determine direction, then classifies
working-timeframe (H4) zones into entries and obstacles.
"""
from market_data import fetch_candles
from storyline_engine import detect_daily_storyline
from zone_detector import detect_all_zones
from zone_filter import filter_zones
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

    # Storyline
    storyline = detect_daily_storyline(pair, daily, h4, debug=False)

    if not storyline:
        print(f"  ❌ No active storyline — skipping classification")
        continue

    direction = storyline['storyline']
    print(f"  ✅ Active storyline: {direction.upper()}")

    # Detect + filter H4 zones
    raw = detect_all_zones(h4, min_open_close_run=2, debug=False)
    zones = filter_zones(raw, h4, pair, debug=False)
    print(f"  Filtered H4 zones: {len(zones)}")

    # Classify
    classified = classify_zones(direction, zones, current_price, pair, debug=True)

    if classified and classified['setups']:
        print(f"\n  Trade setups (entry → obstacle):")
        for i, s in enumerate(classified['setups'][:5], 1):
            e = s['entry']
            o = s['obstacle']
            dist_entry = abs(e['level'] - current_price)
            from zone_filter import PIP_SCALE
            dist_pips = dist_entry / PIP_SCALE.get(pair, 0.0001)

            obs_str = (f"{o['type']:>10} @ {o['level']:.5f} ({s['room_pips']}p away)"
                       if o else "no obstacle in path")
            print(f"    {i}. {e['type']:>10} @ {e['level']:.5f} "
                  f"| {dist_pips:>5.1f}p from price | "
                  f"target: {obs_str}")
    else:
        print(f"\n  No setups — no suitable entry zones in range")
