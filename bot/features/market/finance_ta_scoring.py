"""finance_ta: scoring responsibilities."""
from .finance_ta_common import *  # noqa: F401,F403
from . import finance_ta_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


def _mtf_convergence(mtf: dict) -> tuple:
    """(متن همگرایی، قدرت 1-10)"""
    dirs = mtf.get("dirs") or {}
    scores = mtf.get("scores") or {}
    vals = [dirs.get(k) for k in ("1H", "4H", "1D")]
    bull = sum(1 for d in vals if d == "صعودی")
    bear = sum(1 for d in vals if d == "نزولی")
    avg_sc = [scores.get(k) for k in ("1H", "4H", "1D") if scores.get(k)]
    avg = sum(avg_sc) / len(avg_sc) if avg_sc else 5
    if bull == 3:
        return "همگرایی کامل صعودی ۳/۳", min(10, int(avg + 2))
    if bear == 3:
        return "همگرایی کامل نزولی ۳/۳", min(10, int(avg + 2))
    if bull == 2 and bear == 0:
        return "همگرایی جزئی صعودی ۲/۳", int(avg)
    if bear == 2 and bull == 0:
        return "همگرایی جزئی نزولی ۲/۳", int(avg)
    if bull and bear:
        return "عدم همگرایی — تضاد تایم‌فریم‌ها", max(1, int(avg - 2))
    return "همگرایی ضعیف / رنج", max(1, int(avg - 1))

def _advanced_levels(closes, highs, lows, current=None):
    """محاسبه سطوح حمایت/مقاومت خوشه‌ای بدون وابستگی به finance facade."""
    try:
        c = float(current if current is not None else closes[-1])
    except Exception:
        return {"supports": [], "resistances": []}
    if not closes or not highs or not lows:
        return {"supports": [], "resistances": []}

    vals = []
    # Pivot-like levels from recent extrema and common retracement anchors.
    n = min(len(closes), len(highs), len(lows), 120)
    hs = [float(x) for x in highs[-n:]]
    ls = [float(x) for x in lows[-n:]]
    cs = [float(x) for x in closes[-n:]]
    atr = _atr(hs, ls, cs, 14) or abs(c) * 0.01
    tol = max(atr * 0.55, abs(c) * 0.0025)

    for i in range(2, n - 2):
        if hs[i] >= max(hs[i-2:i+3]): vals.append((hs[i], "swing"))
        if ls[i] <= min(ls[i-2:i+3]): vals.append((ls[i], "swing"))
    for p in (20, 50, 100):
        if n >= p:
            vals.append((max(hs[-p:]), "range"))
            vals.append((min(ls[-p:]), "range"))
    hi, lo = max(hs), min(ls)
    if hi > lo:
        for r in (0.236, 0.382, 0.5, 0.618, 0.786):
            vals.append((hi - (hi - lo) * r, "fib"))

    clusters = []
    for price, source in sorted(vals, key=lambda x: x[0]):
        if price <= 0: continue
        found = None
        for cl in clusters:
            if abs(price - cl["price"]) <= tol:
                found = cl; break
        if found is None:
            clusters.append({"price": price, "touches": 1, "sources": {source}})
        else:
            found["price"] = (found["price"] * found["touches"] + price) / (found["touches"] + 1)
            found["touches"] += 1
            found["sources"].add(source)

    supports, resistances = [], []
    for cl in clusters:
        p = float(cl["price"])
        strength = min(100, 35 + cl["touches"] * 12 + len(cl["sources"]) * 8)
        item = {"price": p, "strength": int(strength)}
        if p < c:
            supports.append(item)
        elif p > c:
            resistances.append(item)
    supports.sort(key=lambda x: (c - x["price"]))
    resistances.sort(key=lambda x: (x["price"] - c))
    return {"supports": supports[:6], "resistances": resistances[:6]}

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

def _professional_score(ta=None, mtf=None, struct=None, derivatives=None, fg=None,
                        current=None, support=None, resistance=None, market=None):
    """امتیاز حرفه‌ای 0..100؛ بدون look-ahead و با وزن‌های محدود و قابل‌تفسیر."""
    ta = ta or {}; mtf = mtf or {}; struct = struct or {}; derivatives = derivatives or {}
    market = market or {}
    trend = 50.0
    t = ta.get("trend")
    if t == "صعودی": trend = 75
    elif t == "نزولی": trend = 25

    rsi = float(ta.get("rsi") or 50)
    momentum = max(0, min(100, 50 + (rsi - 50) * 1.4))
    vr = float(ta.get("vol_ratio") or 1)
    volume = max(0, min(100, 50 + (vr - 1) * 25))
    st = str(struct.get("structure") or "")
    structure = 70 if st.startswith("صعودی") else 30 if st.startswith("نزولی") else 50

    scores = mtf.get("scores") or {}
    mtf_vals = [float(scores[k]) for k in ("1H", "4H", "1D") if scores.get(k) is not None]
    mtf_score = (sum(mtf_vals) / len(mtf_vals) * 10) if mtf_vals else 50

    weights = {"trend": .30, "momentum": .20, "volume": .15, "structure": .20, "mtf": .15}
    raw = (trend*weights["trend"] + momentum*weights["momentum"] + volume*weights["volume"] +
           structure*weights["structure"] + mtf_score*weights["mtf"])
    regime = _market_regime(ta, mtf, vr)
    if regime["label"] == "نوسانی / پرریسک":
        raw = 50 + (raw - 50) * .85
    confidence = max(20, min(95, 55 + abs(raw - 50) * .8 + (5 if mtf_vals else 0)))

    reasons = []
    if ta.get("adx") is not None and float(ta.get("adx") or 0) < 18:
        reasons.append("ADX ضعیف")
    if len(mtf_vals) >= 2:
        dirs = (mtf.get("dirs") or {})
        if len({dirs.get(k) for k in ("1H", "4H", "1D") if dirs.get(k)}) > 1:
            reasons.append("تضاد تایم‌فریم")
    allowed = not (float(ta.get("adx") or 0) < 15)
    gate = {"allowed": allowed, "label": "مجاز" if allowed else "فیلتر شده", "reasons": reasons}
    return {
        "score": round(max(0, min(100, raw)), 1),
        "confidence": round(confidence, 1),
        "factors": {"trend": trend, "momentum": momentum, "volume": volume, "structure": structure},
        "weights": weights,
        "regime": regime,
        "quality_gate": gate,
        "adaptive": {},
    }
