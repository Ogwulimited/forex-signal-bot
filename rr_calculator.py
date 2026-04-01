def calculate_trade_levels(candles, direction, rejection, sweep, tp_lookback=50):
    rejection_candle = rejection["candle"]
    recent = candles[-tp_lookback:] if len(candles) >= tp_lookback else candles

    if direction == "buy":
        entry = rejection_candle["high"]
        sl = min(rejection_candle["low"], sweep["sweep_candle"]["low"])
        tp = max(c["high"] for c in recent)

        if not (sl < entry < tp):
            return None

    elif direction == "sell":
        entry = rejection_candle["low"]
        sl = max(rejection_candle["high"], sweep["sweep_candle"]["high"])
        tp = min(c["low"] for c in recent)

        if not (tp < entry < sl):
            return None

    else:
        return None

    return {
        "entry": round(entry, 5),
        "sl": round(sl, 5),
        "tp": round(tp, 5)
    }

def risk_reward_ok(entry, sl, tp, minimum_rr=2.0):
    risk = abs(entry - sl)
    reward = abs(tp - entry)

    if risk <= 0:
        return False

    rr = reward / risk
    return rr >= minimum_rr
