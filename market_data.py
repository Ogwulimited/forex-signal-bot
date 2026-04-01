import os
import requests

API_KEY = os.getenv("TWELVE_DATA_API_KEY")

def format_symbol(pair):
    if "/" in pair:
        return pair
    return f"{pair[:3]}/{pair[3:]}"

def fetch_candles(pair, interval="5min", outputsize=50):
    if not API_KEY:
        raise ValueError("TWELVE_DATA_API_KEY is missing")

    symbol = format_symbol(pair)

    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": outputsize,
        "apikey": API_KEY,
        "format": "JSON"
    }

    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()
    data = response.json()

    if "values" not in data:
        raise ValueError(f"Invalid API response for {pair}: {data}")

    candles = []
    for row in reversed(data["values"]):
        candles.append({
            "datetime": row["datetime"],
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"])
        })

    return candles
