def is_strong_watchlist_candidate(bias):
    if not bias.get("aligned"):
        return False

    if bias["strength_4h"] < 3:
        return False

    if bias["strength_1h"] < 3:
        return False

    if bias["range_ratio_4h"] < 0.003:
        return False

    if bias["range_ratio_1h"] < 0.0015:
        return False

    return True
