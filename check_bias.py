"""
Diagnostic script to check HTF bias for all pairs.
"""

from mtf_bias_engine import get_mtf_bias

pairs = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]

print("HTF Bias Check\n" + "="*50)
for pair in pairs:
    bias = get_mtf_bias(pair)
    print(f"\n{pair}:")
    print(f"  4H bias: {bias.get('bias_4h')} (strength: {bias.get('strength_4h')}, range_ratio: {bias.get('range_ratio_4h'):.6f})")
    print(f"  1H bias: {bias.get('bias_1h')} (strength: {bias.get('strength_1h')}, range_ratio: {bias.get('range_ratio_1h'):.6f})")
    print(f"  Aligned: {bias.get('aligned')}")
