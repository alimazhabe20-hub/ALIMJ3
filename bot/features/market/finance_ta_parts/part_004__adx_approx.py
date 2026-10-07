# Auto-split part 4: _adx_approx
def _adx_approx(highs: list, lows: list, closes: list, period: int = 14) -> float | None:
    """تقریب ساده ADX"""
    if len(closes) < period * 2:
        return None
    trs = []
    dms_p, dms_m = [], []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        trs.append(tr)
        up = highs[i] - highs[i - 1]
        dn = lows[i - 1] - lows[i]
        dms_p.append(up if up > dn and up > 0 else 0)
        dms_m.append(dn if dn > up and dn > 0 else 0)
    if len(trs) < period:
        return None
    atr = sum(trs[-period:]) / period
    if atr == 0:
        return 0.0
    di_p = 100 * (sum(dms_p[-period:]) / period) / atr
    di_m = 100 * (sum(dms_m[-period:]) / period) / atr
    denom = di_p + di_m
    if denom == 0:
        return 0.0
    dx = 100 * abs(di_p - di_m) / denom
    return dx
