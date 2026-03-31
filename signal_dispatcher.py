from signal_formatter import format_new_signal
from telegram_sender import send_telegram_message

def dispatch_new_signal(trade, pair, timeframe):
    message = format_new_signal(trade, pair, timeframe)
    send_telegram_message(message)
