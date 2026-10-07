# Auto-split part 19: _professional_score
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
