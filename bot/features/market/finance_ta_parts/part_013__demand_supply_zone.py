# Auto-split part 13: _demand_supply_zone
def _demand_supply_zone(highs, lows, closes) -> tuple:
    """بازه تقریبی تقاضا/عرضه از ۱۰–۳۰ کندل قبل"""
    if len(closes) < 30:
        return None, None
    seg_l = lows[-30:-5]
    seg_h = highs[-30:-5]
    if not seg_l or not seg_h:
        return None, None
    demand = (min(seg_l), sorted(seg_l)[max(0, len(seg_l)//4)])
    supply = (sorted(seg_h)[max(0, 3*len(seg_h)//4 - 1)], max(seg_h))
    return demand, supply
