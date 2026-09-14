from market_data_deriv import fetch_candles

for pair in ["EURUSD", "GBPUSD", "USDJPY"]:
    candles = fetch_candles(pair, interval="5min", outputsize=50)
    if candles:
        print(f"{pair}: {len(candles)} candles, last close = {candles[-1]['close']}")
    else:
        print(f"{pair}: FAILED")
