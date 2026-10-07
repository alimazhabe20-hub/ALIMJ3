# Auto-split part 2: detect_regime
def detect_regime(ta=None, mtf=None, vol_ratio=None, closes=None) -> dict:
    ta, mtf = ta or {}, mtf or {}
    adx = float(ta.get("adx") or 0)
    vr = float(vol_ratio or ta.get("vol_ratio") or 1)
    bias = float(mtf.get("bias") or 0)
    chg = float(ta.get("chg_24h_bar") or 0)
    if adx < 18:
        label = "رنج"
    elif vr >= 1.8 and abs(chg) >= 2:
        label = "نوسان شدید"
    elif bias >= .35:
        label = "روند صعودی"
    elif bias <= -.35:
        label = "روند نزولی"
    elif adx >= 25:
        label = "روند خنثی/انتقالی"
    else:
        label = "نوسان کم"
    return {"label": label, "adx": adx, "vol_ratio": vr, "bias": bias, "high_vol": vr >= 1.8}
