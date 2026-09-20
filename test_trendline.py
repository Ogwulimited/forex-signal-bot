from market_data import fetch_candles
from trendline_detector import find_trendlines

PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "USDCAD", "AUDUSD"]

for pair in PAIRS:
    print(f"\n{'='*50}")
    print(f"{pair}")
    print('='*50)
    candles = fetch_candles(pair, interval="1h", outputsize=500)
    if not candles:
        print("Failed to fetch")
        continue
    print(f"Fetched {len(candles)} candles")
    tls = find_trendlines(candles, lookback=250, debug=True)
    for name, tl in tls.items():
        if tl:
            print(f"  ✅ {name.upper()}: touches={tl['touches']} "
                  f"violations={tl['violations']} "
                  f"max_consec={tl['max_consecutive_violations']} "
                  f"slope={tl['slope']:.6f} score={tl['score']}")
        else:
            print(f"  ❌ {name.upper()}: none found")
