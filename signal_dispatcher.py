from market_data import fetch_candles
from breakout_detector import detect_breakout
from retest_detector import detect_retest
from rejection_detector import detect_rejection_candle
from liquidity_sweep_detector import detect_liquidity_sweep
from rr_calculator import calculate_trade_levels, risk_reward_ok
from chop_filter import is_choppy_market

def generate_signal(bias, debug=True, ignore_chop=False):
    if not bias.get("aligned"):
        if debug:
            print("Signal rejected: HTF not aligned.", flush=True)
        return None

    pair = bias["pair"]
    direction = "buy" if bias["bias_4h"] == "bullish" else "sell"

    if debug:
        print(f"5M pipeline started for {pair} | direction={direction}", flush=True)

    candles_5m = fetch_candles(pair, interval="5min", outputsize=100)

    if debug:
        print(f"Fetched {len(candles_5m)} x 5M candles for {pair}", flush=True)

    if not ignore_chop:
        if is_choppy_market(candles_5m):
            if debug:
                print("Signal rejected: market is choppy.", flush=True)
            return None
        elif debug:
            print("Chop filter passed.", flush=True)
    else:
        if debug:
            print("Chop filter bypassed for testing.", flush=True)

    breakout = detect_breakout(candles_5m, direction)
    if not breakout:
        if debug:
            print("Signal rejected: no breakout detected.", flush=True)
        return None
    elif debug:
        print(f"Breakout detected: {breakout}", flush=True)

    retest = detect_retest(candles_5m, breakout, direction)
    if not retest:
        if debug:
            print("Signal rejected: no valid retest found.", flush=True)
        return None
    elif debug:
        print(f"Retest detected: {retest}", flush=True)

    rejection = detect_rejection_candle(candles_5m, direction)
    if not rejection:
        if debug:
            print("Signal rejected: no rejection candle found.", flush=True)
        return None
    elif debug:
        print(f"Rejection candle detected: {rejection}", flush=True)

    sweep = detect_liquidity_sweep(candles_5m, direction)
    if not sweep:
        if debug:
            print("Signal rejected: no liquidity sweep detected.", flush=True)
        return None
    elif debug:
        print(f"Liquidity sweep detected: {sweep}", flush=True)

    trade = calculate_trade_levels(
        candles=candles_5m,
        direction=direction,
        rejection=rejection,
        sweep=sweep
    )

    if not trade:
        if debug:
            print("Signal rejected: invalid trade levels.", flush=True)
        return None
    elif debug:
        print(f"Trade levels calculated: {trade}", flush=True)

    if not risk_reward_ok(trade["entry"], trade["sl"], trade["tp"], minimum_rr=2.0):
        if debug:
            print("Signal rejected: RR below 1:2.", flush=True)
        return None
    elif debug:
        print("Risk/Reward filter passed.", flush=True)

    signal = {
        "pair": pair,
        "timeframe": "5M",
        "type": "BUY" if direction == "buy" else "SELL",
        "entry": trade["entry"],
        "sl": trade["sl"],
        "tp": trade["tp"]
    }

    if debug:
        print(f"Final signal generated: {signal}", flush=True)

    return signal
