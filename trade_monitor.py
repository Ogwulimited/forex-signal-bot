"""
Trade Outcome Monitor
Periodically checks open trades and updates win/loss status.
"""
import json
import os
from datetime import datetime, timezone
from market_data import fetch_candles
from telegram_sender import send_telegram_message

TRADES_FILE = "trades.json"
MAX_TRADE_AGE_HOURS = 48   # Expire trades older than this if unresolved
LOOKBACK_CANDLES = 20      # 5M candles to check (100 minutes)

def load_trades():
    if not os.path.exists(TRADES_FILE):
        return []
    with open(TRADES_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_trades(trades):
    with open(TRADES_FILE, 'w') as f:
        json.dump(trades, f, indent=2)

def parse_timestamp(ts_str):
    """Convert ISO timestamp to datetime."""
    try:
        # Handle 'Z' suffix
        return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
    except Exception:
        return None

def check_trade(trade, candles, direction):
    """
    Determine if a trade hit TP or SL.
    Returns: (status, exit_price, reason)
    """
    tp = trade['tp']
    sl = trade['sl']
    entry = trade['entry']

    for candle in candles:
        high = candle['high']
        low = candle['low']
        close = candle['close']

        if direction == 'buy':
            # TP hit?
            if high >= tp:
                return "win", tp, f"TP reached (high {high:.5f})"
            # SL hit?
            if low <= sl:
                return "loss", sl, f"SL hit (low {low:.5f})"
        else:  # sell
            if low <= tp:
                return "win", tp, f"TP reached (low {low:.5f})"
            if high >= sl:
                return "loss", sl, f"SL hit (high {high:.5f})"

    # No trigger found – check if price moved beyond levels without being captured
    # Use last candle's close to infer
    last_close = candles[-1]['close']
    if direction == 'buy':
        if last_close >= tp:
            return "win", tp, "price beyond TP (inferred)"
        if last_close <= sl:
            return "loss", sl, "price beyond SL (inferred)"
    else:
        if last_close <= tp:
            return "win", tp, "price beyond TP (inferred)"
        if last_close >= sl:
            return "loss", sl, "price beyond SL (inferred)"

    return None, None, None

def format_duration(start, end):
    """Return human‑readable duration."""
    if not start or not end:
        return "unknown"
    delta = end - start
    total_seconds = int(delta.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes = remainder // 60
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"

def main():
    print("Trade monitor started")
    trades = load_trades()
    open_trades = [t for t in trades if t['status'] == 'open']

    if not open_trades:
        print("No open trades")
        return

    # Group by pair to minimise API calls
    pairs = {t['pair'] for t in open_trades}
    candles_cache = {}
    for pair in pairs:
        print(f"Fetching {LOOKBACK_CANDLES} candles for {pair}...")
        candles = fetch_candles(pair, interval='5min', outputsize=LOOKBACK_CANDLES)
        if candles:
            candles_cache[pair] = candles
        else:
            print(f"  Failed to fetch candles for {pair}")

    updated = False
    now = datetime.now(timezone.utc)

    for trade in open_trades:
        pair = trade['pair']
        direction = trade['direction']
        candles = candles_cache.get(pair, [])

        if not candles:
            print(f"Skipping {pair} – no candles")
            continue

        # Expire very old trades
        opened = parse_timestamp(trade['timestamp'])
        if opened:
            age_hours = (now - opened).total_seconds() / 3600
            if age_hours > MAX_TRADE_AGE_HOURS:
                trade['status'] = 'expired'
                trade['exit_reason'] = f"Expired after {age_hours:.1f}h"
                trade['exit_time'] = now.isoformat()
                print(f"Trade {trade['id']} expired")
                updated = True
                # Send message?
                message = f"⏰ {pair} {direction.upper()} EXPIRED | Duration: {format_duration(opened, now)} | RR: {trade['rr']}"
                send_telegram_message(message)
                continue

        status, price, reason = check_trade(trade, candles, direction)

        if status:
            trade['status'] = status
            trade['exit_price'] = price
            trade['exit_reason'] = reason
            trade['exit_time'] = now.isoformat()
            updated = True

            # Calculate R-multiple
            entry = trade['entry']
            sl = trade['sl']
            risk = abs(entry - sl)
            reward = abs(entry - price) if price else 0
            r_multiple = reward / risk if risk > 0 else 0
            trade['r_multiple'] = round(r_multiple, 2)

            # Duration
            dur = format_duration(opened, now) if opened else "unknown"

            # Emoji
            emoji = "✅" if status == "win" else "❌"
            message = (
                f"{emoji} {pair} {direction.upper()} {status.upper()}\n"
                f"Exit: {price:.5f} ({reason})\n"
                f"R‑multiple: {r_multiple:.2f}R | Duration: {dur}"
            )
            print(f"Trade {trade['id']} -> {status}")
            send_telegram_message(message)

    if updated:
        save_trades(trades)
        print("Trades updated")

if __name__ == "__main__":
    main()
