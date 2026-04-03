def is_choppy_market(candles, lookback=20, min_range_ratio=0.0015):
    if len(candles) < lookback:
        return True

    recent = candles[-lookback:]
    high = max(c["high"] for c in recent)
    low = min(c["low"] for c in recent)
    avg_close = sum(c["close"] for c in recent) / len(recent)

    if avg_close <= 0:
        return True

    range_ratio = (high - low) / avg_close

    print(f"Chop filter debug | range_ratio={range_ratio:.6f} | threshold={min_range_ratio}", flush=True)

    return range_ratio < min_range_ratio
