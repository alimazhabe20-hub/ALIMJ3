# Auto-split part 18: _market_regime
def _market_regime(ta=None, mtf=None, vol_ratio=None):
    """طبقه‌بندی ساده و پایدار رژیم بازار برای موتور امتیازدهی."""
    ta = ta or {}; mtf = mtf or {}
    adx = float(ta.get("adx") or 0)
    rsi = float(ta.get("rsi") or 50)
    vr = float(vol_ratio if vol_ratio is not None else ta.get("vol_ratio") or 1)
    dirs = mtf.get("dirs") or {}
    trend_votes = [dirs.get(k) for k in ("1H", "4H", "1D")]
    bull = trend_votes.count("صعودی")
    bear = trend_votes.count("نزولی")
    if adx < 18:
        label = "رنج / نوسان کم"
    elif bull >= 2 and rsi >= 50:
        label = "روند صعودی"
    elif bear >= 2 and rsi <= 50:
        label = "روند نزولی"
    elif vr >= 1.8:
        label = "نوسانی / پرریسک"
    else:
        label = "انتقالی / مختلط"
    return {"label": label, "adx": round(adx, 2), "vol_ratio": round(vr, 2)}
