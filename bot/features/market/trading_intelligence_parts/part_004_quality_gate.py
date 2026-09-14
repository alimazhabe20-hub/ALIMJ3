# Auto-split part 4: quality_gate
def quality_gate(score: float, confidence: float, mtf=None, data_quality: float = 100, regime=None) -> dict:
    mtf = mtf or {}
    conflict = bool(mtf.get("conflict"))
    reasons = []
    if data_quality < 60: reasons.append("کیفیت داده پایین")
    if confidence < 55: reasons.append("اطمینان پایین")
    if conflict: reasons.append("تضاد تایم‌فریم")
    if mtf.get("force_wait"): reasons.append("ADX روزانه ضعیف")
    if abs(float(score) - 50) < 8: reasons.append("برتری جهت‌دار کافی نیست")
    blocked = bool(reasons)
    return {"allowed": not blocked, "reasons": reasons, "label": "تأیید نسبی" if not blocked else "صبر / عدم‌تأیید"}
