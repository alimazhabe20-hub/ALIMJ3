def _looks_truncated(answer: str) -> bool:
    """تشخیص تقریبی پاسخ ناقص (برای پیشنهاد دکمه ادامه)."""
    a = (answer or "").strip()
    if len(a) < 1200:
        return False
    # اگر خیلی بلند است یا با علائم ناتمام تمام شده
    if len(a) >= 2800:
        return True
    if a.endswith(("...", "…", ":", "—", "-", ",")):
        return True
    # جمله کامل تمام نشده
    if not re.search(r"[.!?؟۔]\s*$", a) and len(a) > 1600:
        return True
    return False
