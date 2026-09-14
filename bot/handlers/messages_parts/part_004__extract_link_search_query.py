def _extract_link_search_query(text: str, last_answer: str | None) -> str:
    """از درخواست «لینکش بفرست» و پاسخ قبلی، عبارت مناسب جستجو را استخراج می‌کند."""
    normalized = (text or "").strip().replace("‌", " ")
    if not re.search(r"(?:لینک|لینکش|لینک\s*خرید|آدرس|لینک\s*بفرست)", normalized, re.I):
        return ""
    answer = (last_answer or "").strip()
    if not answer:
        return ""
    # اول عبارت داخل گیومه فارسی/انگلیسی؛ معمولاً همان عبارت خرید است.
    patterns = [
        r"«([^»]{3,120})»",
        r"[\"']([^\"']{3,120})[\"']",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, answer)
        if matches:
            candidate = matches[-1].strip()
            if not re.search(r"^(لینک|آدرس|این|محصول|برند)", candidate, re.I):
                return candidate
    # اگر نقل‌قول نبود، از خطوطی که عبارت جستجو را معرفی می‌کنند استفاده کن.
    m = re.search(r"(?:عبارت|سرچ|جستجو)\s*(?:«([^»]+)»|[:：]\s*(.+))", answer, re.I)
    if m:
        return (m.group(1) or m.group(2) or "").strip()[:160]
    return ""
