"""
Test the MSNR zone detector + filter pipeline.
"""
from market_data import fetch_candles
from zone_detector import detect_all_zones
from zone_filter import filter_zones

PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "USDCAD", "AUDUSD"]

for pair in PAIRS:
    print(f"\n{'=' * 60}")
    print(f"{pair} — 1H candles")
    print('=' * 60)

    candles = fetch_candles(pair, interval="1h", outputsize=300)
    if not candles:
        print("  Failed to fetch candles")
        continue

    current = candles[-1]['close']
    print(f"  Fetched {len(candles)} candles | current price ≈ {current:.5f}")

    # Raw detection
    raw = detect_all_zones(candles, min_open_close_run=2, debug=True)

    # Filter pipeline
    filtered = filter_zones(raw, candles, pair, debug=True)

    print(f"\n  Actionable zones after filter: {len(filtered)}")
    print(f"  Top 5 ranked zones:")
    for z in filtered[:5]:
        print(f"    {z['type']:>10} @ {z['level']:.5f} "
              f"| score={z['score']:>5} "
              f"| cluster={z['cluster_count']} "
              f"| patterns={z['patterns']} "
              f"| idx={z['index']}")
