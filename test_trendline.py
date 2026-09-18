from market_data import fetch_candles
from trendline_detector import find_trendlines

PAIRS = ["EURUSD", "GBPUSD", "USDJPY"]

for pair in PAIRS:
    print(f"\n{'='*50}")
    print(f"{pair}")
    print('='*50)
    candles = fetch_candles(pair, interval="1h", outputsize=200)
    if not candles:
        print("Failed to fetch")
        continue
    print(f"Fetched {len(candles)} candles")
    tls = find_trendlines(candles, lookback=100, debug=True)
    for name, tl in tls.items():
        if tl:
            print(f"  ✅ {name.upper()}: touches={tl['touches']} "
                  f"violations={tl['violations']} slope={tl['slope']:.6f} "
                  f"score={tl['score']}")
        else:
            print(f"  ❌ {name.upper()}: none found")
