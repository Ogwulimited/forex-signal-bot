"""
Test MSNR zone detector + filter v2.
"""
from market_data import fetch_candles
from zone_detector import detect_all_zones
from zone_filter import filter_zones, PIP_SCALE

PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "USDCAD", "AUDUSD"]

for pair in PAIRS:
    print(f"\n{'=' * 62}")
    print(f"{pair} — 1H candles")
    print('=' * 62)

    candles = fetch_candles(pair, interval="1h", outputsize=300)
    if not candles:
        print("  Failed to fetch candles")
        continue

    current = candles[-1]['close']
    pip = PIP_SCALE.get(pair, 0.0001)

    raw = detect_all_zones(candles, min_open_close_run=2, debug=True)
    filtered = filter_zones(raw, candles, pair, debug=True)

    print(f"\n  Current price: {current:.5f}")
    print(f"  Actionable zones: {len(filtered)}")
    for z in filtered:
        dist_pips = abs(z['level'] - current) / pip
        print(f"    {z['type']:>10} @ {z['level']:.5f} "
              f"| dist={dist_pips:>5.1f}p "
              f"| score={z['score']:>5} "
              f"| cluster={z['cluster_count']:>3} "
              f"| patterns={z['patterns']}")
