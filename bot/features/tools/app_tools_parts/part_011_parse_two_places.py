# Auto-split part 11: parse_two_places
def parse_two_places(text: str):
    """استخراج دو مکان از متن کاربر — دقیق‌تر از قبل"""
    t = (text or "").strip()
    if not t:
        return None

    # جداکننده‌های صریح
    for sep in [
        " تا ", " به ", " -> ", " → ", " — ", " – ",
        " to ", " - ", "\t", "،", ",",
    ]:
        if sep in t:
            a, b = [p.strip() for p in t.split(sep, 1)]
            if a and b:
                return a, b

    # اگر کل متن دو مکان معروف پشت‌سرهم باشد
    low = _norm_place(t)
    # چندکلمه‌ای از ابتدا
    for mw in _MULTIWORD:
        if low.startswith(mw + " "):
            rest = t[len(mw):].strip() if len(t) >= len(mw) else ""
            # try original length match approximately
            rest = low[len(mw):].strip()
            if rest:
                return mw, rest
        if low.endswith(" " + mw):
            first = low[: -len(mw)].strip()
            if first:
                return first, mw

    # دو توکن فارسی/انگلیسی ساده
    parts = t.split()
    if len(parts) == 2:
        return parts[0], parts[1]
    if len(parts) == 3:
        # احتمال: New York London  یا  تهران شهرکرد ؟
        # امتحان 2+1 و 1+2
        return None  # بهتر است کاربر جداکننده بگذارد
    if len(parts) == 4:
        return f"{parts[0]} {parts[1]}", f"{parts[2]} {parts[3]}"
    if len(parts) > 2:
        mid = len(parts) // 2
        return " ".join(parts[:mid]), " ".join(parts[mid:])
    return None
