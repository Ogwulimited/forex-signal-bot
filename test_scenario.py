from market_data import fetch_candles
from mtf_bias_engine import get_mtf_bias
from trendline_detector import find_trendlines
from scenario_classifier import classify_scenario, find_protected_level

PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "USDCAD", "AUDUSD"]

for pair in PAIRS:
    print(f"\n{'='*55}")
    print(f"{pair}")
    print('='*55)

    candles_1h = fetch_candles(pair, interval="1h", outputsize=500)
    if not candles_1h:
        print("Failed to fetch 1H candles")
        continue

    print(f"Fetched {len(candles_1h)} 1H candles")

    bias_data = get_mtf_bias(pair)
    if not bias_data:
        print("Failed to get MTF bias")
        continue

    print(f"4H bias: {bias_data['bias_4h']} | 1H bias: {bias_data['bias_1h']} | "
          f"Aligned: {bias_data['aligned']}")

    tls = find_trendlines(candles_1h, lookback=250, debug=False)
    print(f"Trendlines: resistance={'yes' if tls['resistance'] else 'no'}, "
          f"support={'yes' if tls['support'] else 'no'}")

    scenario = classify_scenario(bias_data, tls, candles_1h, debug=True)

    if scenario:
        print(f"\n  ✅ SCENARIO: {scenario['scenario']} → {scenario['direction'].upper()}")
        bi = scenario["break_info"]
        print(f"     Break index: {bi['break_index']}, "
              f"bars beyond: {bi['consecutive_bars']}, "
              f"price at break: {bi['price_at_break']:.5f}")

        protected = find_protected_level(
            candles_1h, scenario["direction"], bi["break_index"]
        )
        if protected:
            print(f"     Protected {protected['type']}: "
                  f"{protected['level']:.5f} (index {protected['index']})")
        else:
            print("     No protected level found")
    else:
        print("  ❌ No active scenario")
