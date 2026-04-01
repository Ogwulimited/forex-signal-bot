def generate_signal(bias):
    if bias["pair"] == "EURUSD":
        return {
            "pair": bias["pair"],
            "timeframe": "5M",
            "type": "BUY",
            "entry": 1.1000,
            "sl": 1.0950,
            "tp": 1.1100
        }
    return None
