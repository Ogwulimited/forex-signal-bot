def evaluate_mtf_bias(htf_structure, htf_bos, mtf_structure, mtf_bos, ltf_direction):
    if htf_structure["trend"] == ltf_direction and mtf_structure["trend"] == ltf_direction:
        return {"trade_allowed": True}
    return {"trade_allowed": False}
