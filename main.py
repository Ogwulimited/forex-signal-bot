from mtf_bias_engine import evaluate_mtf_bias
from signal_dispatcher import dispatch_new_signal

def run_bot():
    htf_structure = {"trend": "bullish"}
    htf_bos = [{"direction": "bullish", "strength": "strong"}]

    mtf_structure = {"trend": "bullish"}
    mtf_bos = [{"direction": "bullish", "strength": "strong"}]

    ltf_direction = "bullish"

    mtf_result = evaluate_mtf_bias(
        htf_structure, htf_bos,
        mtf_structure, mtf_bos,
        ltf_direction
    )

    if not mtf_result["trade_allowed"]:
        print("No trade")
        return

    trade = {
        "direction": "bullish",
        "entry": 1.1000,
        "stop_loss": 1.0950,
        "take_profit": 1.1100,
        "rr": 2
    }

    dispatch_new_signal(trade, "EURUSD", "5M")

if __name__ == "__main__":
    run_bot()
