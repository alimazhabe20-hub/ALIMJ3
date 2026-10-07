# Auto-split part 15: _compute_bias
def _compute_bias(
    ext: dict,
    internal: dict,
    fvgs: list,
    obs: list,
    liq: dict,
    dr: dict,
    disp: dict | None,
) -> dict:
    score = 0.0
    reasons: list[str] = []

    if ext.get("phase") == "bullish":
        score += 2.5
        reasons.append("ساختار خارجی صعودی")
    elif ext.get("phase") == "bearish":
        score -= 2.5
        reasons.append("ساختار خارجی نزولی")

    if ext.get("bos"):
        if ext["bos"]["side"] == "bullish":
            score += 1.5
            reasons.append("BOS صعودی")
        else:
            score -= 1.5
            reasons.append("BOS نزولی")
    if ext.get("mss"):
        if ext["mss"].get("side") == "bullish":
            score += 2.0
            reasons.append("MSS صعودی")
        elif ext["mss"].get("side") == "bearish":
            score -= 2.0
            reasons.append("MSS نزولی")

    if internal.get("phase") == "bullish":
        score += 0.8
    elif internal.get("phase") == "bearish":
        score -= 0.8

    open_bull = sum(1 for g in fvgs if g["type"] == "bullish" and g["state"] in ("open", "partial"))
    open_bear = sum(1 for g in fvgs if g["type"] == "bearish" and g["state"] in ("open", "partial"))
    if open_bull > open_bear:
        score += 0.7
        reasons.append("FVGهای صعودی فعال‌تر")
    elif open_bear > open_bull:
        score -= 0.7
        reasons.append("FVGهای نزولی فعال‌تر")

    bull_ob = sum(1 for b in obs if b["side"] == "bullish" and not b["broken"])
    bear_ob = sum(1 for b in obs if b["side"] == "bearish" and not b["broken"])
    if bull_ob > bear_ob:
        score += 0.5
    elif bear_ob > bull_ob:
        score -= 0.5

    if dr.get("zone") == "Discount":
        score += 1.0
        reasons.append("قیمت در Discount")
    elif dr.get("zone") == "Premium":
        score -= 1.0
        reasons.append("قیمت در Premium")

    if dr.get("in_bull_ote"):
        score += 0.8
        reasons.append("داخل OTE صعودی")
    if dr.get("in_bear_ote"):
        score -= 0.8
        reasons.append("داخل OTE نزولی")

    sweep = liq.get("sweep")
    if sweep:
        if sweep["side"] == "ssl":
            score += 1.2
            reasons.append("Sweep کف (جذب نقدینگی فروش)")
        elif sweep["side"] == "bsl":
            score -= 1.2
            reasons.append("Sweep سقف (جذب نقدینگی خرید)")

    if disp:
        if disp["side"] == "bullish":
            score += min(1.5, disp["score"] * 0.35)
            reasons.append(disp["text"])
        else:
            score -= min(1.5, disp["score"] * 0.35)
            reasons.append(disp["text"])

    # confidence from |score| and agreement
    conf = min(95.0, 40.0 + abs(score) * 8.0)
    if ext.get("phase") in ("bullish", "bearish") and internal.get("phase") == ext.get("phase"):
        conf = min(95.0, conf + 8.0)
        reasons.append("هم‌راستایی ساختار داخلی و خارجی")

    if score >= 2.5:
        bias = "صعودی قوی (Strong Bullish)"
        side = "bullish"
    elif score >= 1.0:
        bias = "صعودی ملایم (Mild Bullish)"
        side = "bullish"
    elif score <= -2.5:
        bias = "نزولی قوی (Strong Bearish)"
        side = "bearish"
    elif score <= -1.0:
        bias = "نزولی ملایم (Mild Bearish)"
        side = "bearish"
    else:
        bias = "خنثی / منتظر تأیید (Neutral)"
        side = "neutral"
        conf = min(conf, 55.0)

    return {
        "bias": bias,
        "side": side,
        "score": round(score, 2),
        "confidence": round(conf, 1),
        "reasons": reasons[:8],
    }
