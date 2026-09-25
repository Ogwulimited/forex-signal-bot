"""
Test the MSNR zone detector on real 1H candles.
"""
from market_data import fetch_candles
from zone_detector import detect_all_zones

PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "USDCAD", "AUDUSD"]

for pair in PAIRS:
    print(f"\n{'=' * 55}")
    print(f"{pair} — 1H candles")
    print('=' * 55)

    candles = fetch_candles(pair, interval="1h", outputsize=300)
    if not candles:
        print("  Failed to fetch candles")
        continue

    print(f"  Fetched {len(candles)} candles")

    zones = detect_all_zones(candles, min_open_close_run=2, debug=True)

    # Summary counts
    a_count = sum(1 for z in zones if z['pattern'] == 'A')
    v_count = sum(1 for z in zones if z['pattern'] == 'V')
    oc_count = sum(1 for z in zones if z['pattern'] == 'open_close')
    res_count = sum(1 for z in zones if z['type'] == 'resistance')
    sup_count = sum(1 for z in zones if z['type'] == 'support')

    print(f"  Summary:")
    print(f"    A (resistance):        {a_count}")
    print(f"    V (support):           {v_count}")
    print(f"    Open-close levels:     {oc_count}")
    print(f"    Total resistance zones: {res_count}")
    print(f"    Total support zones:    {sup_count}")

    # Show the 3 most recent zones for inspection
    print(f"  Most recent 3 zones:")
    for z in zones[-3:]:
        print(f"    [{z['pattern']}] {z['type']} @ {z['level']:.5f} "
              f"(idx {z['index']})")
