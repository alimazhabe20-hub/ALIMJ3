# Auto-split part 10: _market_structure
def _market_structure(highs, lows, closes) -> dict:
    """ساختار ساده: HH/HL یا LH/LL + BOS تقریبی"""
    if len(closes) < 20:
        return {"structure": "نامشخص", "bos": None}
    # swing تقریبی روی 5 کندل
    def swings(arr, mode="high"):
        pts = []
        for i in range(2, len(arr) - 2):
            if mode == "high" and arr[i] == max(arr[i-2:i+3]):
                pts.append((i, arr[i]))
            if mode == "low" and arr[i] == min(arr[i-2:i+3]):
                pts.append((i, arr[i]))
        return pts[-4:]
    sh = swings(highs, "high")
    sl = swings(lows, "low")
    structure = "رنج"
    bos = None
    if len(sh) >= 2 and len(sl) >= 2:
        if sh[-1][1] > sh[-2][1] and sl[-1][1] > sl[-2][1]:
            structure = "صعودی (HH/HL)"
            if closes[-1] > sh[-1][1]:
                bos = "BOS صعودی — شکست سقف اخیر"
        elif sh[-1][1] < sh[-2][1] and sl[-1][1] < sl[-2][1]:
            structure = "نزولی (LH/LL)"
            if closes[-1] < sl[-1][1]:
                bos = "BOS نزولی — شکست کف اخیر"
        elif sh[-1][1] < sh[-2][1] and sl[-1][1] > sl[-2][1]:
            structure = "احتمال CHOCH / فشردگی"
            bos = "تغییر ساختار محتمل"
    return {"structure": structure, "bos": bos, "last_swing_high": sh[-1][1] if sh else None, "last_swing_low": sl[-1][1] if sl else None}
