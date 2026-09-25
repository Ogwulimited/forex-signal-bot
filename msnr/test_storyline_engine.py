"""
Test the storyline engine across all pairs.
"""
from market_data import fetch_candles
from storyline_engine import detect_daily_storyline

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

    print(f"  Daily candles: {len(daily)} | "
          f"last close = {daily[-1]['close']:.5f}")
    print(f"  H4 candles:    {len(h4)} | "
          f"last close = {h4[-1]['close']:.5f}")

    storyline = detect_daily_storyline(pair, daily, h4, debug=True)

    if storyline:
        print(f"\n  ✅ ACTIVE STORYLINE: {storyline['storyline'].upper()}")
        print(f"     Daily rejection @ zone level "
              f"{storyline['rejection_zone']['level']:.5f}")
        print(f"     H4 QM: {storyline['h4_qm']['direction']} break "
              f"({storyline['h4_qm']['candles_since_break']} candles ago)")
    else:
        print(f"\n  ❌ No active storyline")
