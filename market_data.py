"""
Market Data Module – Powered by Deriv API
Paginated fetcher for historical candles.
"""

import json
import time
import websocket

WS_URL = "wss://api.derivws.com/trading/v1/options/ws/public"

SYMBOL_MAP = {
    "EURUSD": "frxEURUSD", "GBPUSD": "frxGBPUSD", "USDJPY": "frxUSDJPY",
    "AUDUSD": "frxAUDUSD", "USDCAD": "frxUSDCAD", "USDCHF": "frxUSDCHF",
    "NZDUSD": "frxNZDUSD", "EURGBP": "frxEURGBP", "EURJPY": "frxEURJPY",
    "GBPJPY": "frxGBPJPY", "AUDJPY": "frxAUDJPY", "EURCHF": "frxEURCHF",
    "EURAUD": "frxEURAUD", "EURCAD": "frxEURCAD", "GBPAUD": "frxGBPAUD",
    "GBPCAD": "frxGBPCAD", "GBPCHF": "frxGBPCHF", "AUDCAD": "frxAUDCAD",
    "AUDCHF": "frxAUDCHF", "AUDNZD": "frxAUDNZD", "NZDJPY": "frxNZDJPY",
    "CADJPY": "frxCADJPY", "CHFJPY": "frxCHFJPY", "USDTRY": "frxUSDTRY",
    "USDZAR": "frxUSDZAR", "USDMXN": "frxUSDMXN", "USDNOK": "frxUSDNOK",
    "USDSEK": "frxUSDSEK", "USDSGD": "frxUSDSGD", "USDPLN": "frxUSDPLN",
    "EURNZD": "frxEURNZD", "GBPNZD": "frxGBPNZD", "CADCHF": "frxCADCHF",
    "NZDCAD": "frxNZDCAD", "NZDCHF": "frxNZDCHF", "GBPSEK": "frxGBPSEK",
    "XAUUSD": "frxXAUUSD",
}

TIMEFRAME_MAP = {
    "1min": 60, "5min": 300, "15min": 900, "30min": 1800,
    "1h": 3600, "4h": 14400, "1day": 86400,
}


def _fetch_chunk(symbol, granularity, count, end):
    ws = websocket.create_connection(WS_URL, timeout=30)
    request = {
        "ticks_history": symbol,
        "adjust_start_time": 1,
        "count": count,
        "end": end,
        "style": "candles",
        "granularity": granularity,
    }
    ws.send(json.dumps(request))
    for _ in range(5):
        raw = ws.recv()
        resp = json.loads(raw)
        if "candles" in resp:
            ws.close()
            return resp["candles"]
        if "error" in resp:
            ws.close()
            raise Exception(f"Deriv error: {resp['error']}")
    ws.close()
    return []


def fetch_candles(pair, interval="5min", outputsize=100, max_iterations=500):
    symbol = SYMBOL_MAP.get(pair.upper())
    if not symbol:
        print(f"Unknown pair: {pair}")
        return []

    granularity = TIMEFRAME_MAP.get(interval)
    if not granularity:
        print(f"Unknown interval: {interval}")
        return []

    all_candles = []
    seen_epochs = set()
    end = "latest"
    remaining = outputsize
    iterations = 0

    while remaining > 0 and iterations < max_iterations:
        iterations += 1
        take = min(5000, remaining)
        try:
            chunk = _fetch_chunk(symbol, granularity, take, end)
        except Exception as e:
            print(f"    Fetch error (iter {iterations}): {e}")
            break

        if not chunk:
            break

        new_candles = [c for c in chunk if int(c["epoch"]) not in seen_epochs]
        if not new_candles:
            break

        for c in new_candles:
            seen_epochs.add(int(c["epoch"]))

        all_candles = new_candles + all_candles
        remaining -= len(new_candles)

        earliest = min(int(c["epoch"]) for c in new_candles)
        end = earliest - 1
        time.sleep(0.2)

    return [
        {
            "datetime": int(c["epoch"]),
            "open": float(c["open"]),
            "high": float(c["high"]),
            "low": float(c["low"]),
            "close": float(c["close"]),
        }
        for c in sorted(all_candles, key=lambda x: int(x["epoch"]))
]
