"""
Test the QM detector on H4 and H1 candles.
QM is used at two pipeline points:
  - H4 (for Daily storyline confirmation)
  - H1 (for confirmation entry)
"""
from market_data import fetch_candles
from qm_detector import detect_qm

PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "USDCAD", "AUDUSD"]

for pair in PAIRS:
    print(f"\n{'=' * 62}")
    print(f"{pair}")
    print('=' * 62)

    # H4 QM check
    print(f"\n  ── H4 QM (storyline leg) ──")
    h4 = fetch_candles(pair, interval="4h", outputsize=200)
    if h4:
        print(f"  Fetched {len(h4)} H4 candles | last close = {h4[-1]['close']:.5f}")
        bull = detect_qm(h4, 'bullish', pair=pair, debug=True)
        bear = detect_qm(h4, 'bearish', pair=pair, debug=True)
        if bull:
            print(f"  → BULLISH QM at candle {bull['break_index']} "
                  f"({bull['candles_since_break']} candles ago)")
        if bear:
            print(f"  → BEARISH QM at candle {bear['break_index']} "
                  f"({bear['candles_since_break']} candles ago)")
        if not bull and not bear:
            print(f"  → No QM active on H4")

    # H1 QM check
    print(f"\n  ── H1 QM (entry leg) ──")
    h1 = fetch_candles(pair, interval="1h", outputsize=300)
    if h1:
        print(f"  Fetched {len(h1)} H1 candles | last close = {h1[-1]['close']:.5f}")
        bull = detect_qm(h1, 'bullish', pair=pair, debug=True)
        bear = detect_qm(h1, 'bearish', pair=pair, debug=True)
        if bull:
            print(f"  → BULLISH QM at candle {bull['break_index']} "
                  f"({bull['candles_since_break']} candles ago)")
        if bear:
            print(f"  → BEARISH QM at candle {bear['break_index']} "
                  f"({bear['candles_since_break']} candles ago)")
        if not bull and not bear:
            print(f"  → No QM active on H1")
