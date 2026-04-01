def is_strong_watchlist_candidate(bias):
    if not bias.get("aligned"):
        return False

    # Require HTF and MTF direction to be strong enough
    if bias["strength_4h"] < 2:
        return False

    if bias["strength_1h"] < 2:
        return False

    # Reject compressed / low-range markets
    if bias["range_ratio_4h"] < 0.003:
        return False

    if bias["range_ratio_1h"] < 0.0015:
        return False

    return True
