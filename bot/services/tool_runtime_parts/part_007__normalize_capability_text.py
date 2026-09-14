# Auto-split part 7: _normalize_capability_text
def _normalize_capability_text(text: str) -> str:
    """نرمال‌سازی سبک برای Router بدون تغییر متن اصلی ارسالی به مدل."""
    text = (text or "").strip().lower()
    text = text.replace("ي", "ی").replace("ك", "ک")
    text = re.sub(r"[ـ‌‍]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text
