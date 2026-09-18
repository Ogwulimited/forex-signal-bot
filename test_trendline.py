from market_data import fetch_candles
from trendline_detector import find_trendlines

PAIR = "EURUSD"

candles = fetch_candles(PAIR, interval="1h", outputsize=200)
if not candles:
    print("Failed to fetch candles")
else:
    print(f"Fetched {len(candles)} candles for {PAIR}")
    tls = find_trendlines(candles, lookback=100, debug=True)
    for name, tl in tls.items():
        if tl:
            print(f"\n{name.upper()} trendline:")
            print(f"  Slope: {tl['slope']:.6f}")
            print(f"  Touches: {tl['touches']}")
            print(f"  Violations: {tl['violations']}")
            print(f"  Score: {tl['score']}")
        else:
            print(f"\n{name.upper()}: no valid trendline found")
