"""
Market Data Module – Deriv API (New v1 Public Endpoint)
Fetches historical candles via Deriv's public WebSocket API.
No App ID or authentication required for market data.
"""
import json
import time
import websocket

# New public WebSocket endpoint – no app_id needed
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
}

TIMEFRAME_MAP = {
    "1min": 60, "5min": 300, "15min": 900, "30min": 1800,
    "1h": 3600, "4h": 14400, "1day": 86400,
}

def fetch_candles(pair, interval="5min", outputsize=100, retries=3):
    """
    Fetch historical candles from Deriv's public WebSocket API.
    Returns list of dicts: {'datetime', 'open', 'high', 'low', 'close'} or [].
    """
    symbol = SYMBOL_MAP.get(pair.upper())
    if not symbol:
        print(f"Unknown pair: {pair}")
        return []

    granularity = TIMEFRAME_MAP.get(interval)
    if not granularity:
        print(f"Unknown interval: {interval}")
        return []

    for attempt in range(retries):
        try:
            ws = websocket.create_connection(WS_URL, timeout=15)

            request = {
                "ticks_history": symbol,
                "adjust_start_time": 1,
                "count": outputsize,
                "end": "latest",
                "start": 1,
                "style": "candles",
                "granularity": granularity,
            }

            ws.send(json.dumps(request))

            # Read up to 5 messages looking for 'candles'
            for _ in range(5):
                raw = ws.recv()
                response = json.loads(raw)

                if "candles" in response:
                    ws.close()
                    return [
                        {
                            "datetime": c["epoch"],
                            "open": float(c["open"]),
                            "high": float(c["high"]),
                            "low": float(c["low"]),
                            "close": float(c["close"]),
                        }
                        for c in response["candles"]
                    ]

                if "error" in response:
                    print(f"Deriv error for {pair}: {response['error'].get('message')}")
                    ws.close()
                    return []

            ws.close()

        except Exception as e:
            print(f"Attempt {attempt+1} failed for {pair}: {e}")
            time.sleep(2)

    return []
