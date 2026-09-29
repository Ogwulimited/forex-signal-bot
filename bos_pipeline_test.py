"""
Test the BOS pipeline on all pairs.
"""
from market_data import fetch_candles
from bos_pipeline import generate_signal

PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "USDCAD", "AUDUSD", "XAUUSD"]

signals_found = 0

for pair in PAIRS:
    print(f"\n{'=' * 62}")
    print(f"{pair}")
    print('=' * 62)

    h5 = fetch_candles(pair, interval="5min", outputsize=100)
    h1 = fetch_candles(pair, interval="1h", outputsize=200)
    h4 = fetch_candles(pair, interval="4h", outputsize=100)

    if not h5 or not h1 or not h4:
        print("  Fetch failed")
        continue

    print(f"  5M={len(h5)} 1H={len(h1)} 4H={len(h4)}")

    signal = generate_signal(pair, h5, h1, h4, debug=True)

    if signal:
        signals_found += 1
        print(f"\n  📊 {signal['direction'].upper()} {pair}")
        print(f"     Entry: {signal['entry']:.5f}")
        print(f"     SL:    {signal['sl']:.5f}")
        print(f"     TP:    {signal['tp']:.5f}")
        print(f"     RR:    {signal['rr']:.2f}")
        print(f"     Regime: {signal['regime']}")

print(f"\n{'=' * 62}")
print(f"TOTAL SIGNALS: {signals_found}")
print('=' * 62)
