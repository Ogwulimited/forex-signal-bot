"""
Test BOS structure + regime detection.
"""
from market_data import fetch_candles
from bos_structure import analyze as analyze_structure, detect_choch
from bos_regime import get_regime

PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "USDCAD", "AUDUSD", "XAUUSD"]

for pair in PAIRS:
    print(f"\n{'=' * 62}")
    print(f"{pair}")
    print('=' * 62)

    h4 = fetch_candles(pair, interval="4h", outputsize=100)
    h1 = fetch_candles(pair, interval="1h", outputsize=200)

    if not h4 or not h1:
        print("  Fetch failed")
        continue

    print(f"  4H candles: {len(h4)} | last close: {h4[-1]['close']:.5f}")
    print(f"  1H candles: {len(h1)} | last close: {h1[-1]['close']:.5f}")

    s4 = analyze_structure(h4, debug=False)
    s1 = analyze_structure(h1, debug=False)

    print(f"\n  ── 4H Structure ──")
    print(f"    State: {s4.get('state')}")
    print(f"    Highs: {s4.get('highs_labels')}")
    print(f"    Lows:  {s4.get('lows_labels')}")

    print(f"\n  ── 1H Structure ──")
    print(f"    State: {s1.get('state')}")
    print(f"    Highs: {s1.get('highs_labels')}")
    print(f"    Lows:  {s1.get('lows_labels')}")

    choch = detect_choch(h1, s1)
    if choch:
        print(f"\n  ── CHoCH on 1H ──")
        print(f"    Type: {choch['type']}")
        print(f"    Break level: {choch['break_level']:.5f}")
        print(f"    Candles since: {choch['candles_since']}")
    else:
        print(f"\n  ── No CHoCH on 1H ──")

    regime = get_regime(h4, h1, debug=False)
    print(f"\n  ── REGIME ──")
    print(f"    {regime['regime']}")
    print(f"    Trade direction: {regime['trade_direction']}")
