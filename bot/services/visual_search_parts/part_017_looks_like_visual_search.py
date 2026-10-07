# Auto-split part 17: looks_like_visual_search
def looks_like_visual_search(text: str) -> bool:
    """Return True for explicit Lens / image-search requests."""
    t = _normalize(text)
    patterns = (
        "گوگل لنز", "لنز", "جستجوی عکس", "جستجوی تصویری", "سرچ عکس", "سرچ تصویری",
        "این عکس چیه", "این تصویر چیه", "پیدا کن عکس", "پیدا کن تصویر",
        "محصول مشابه", "محصول شبیه", "مشابه این عکس", "what is this", "search image",
        "visual search", "find similar", "find this product", "shop by image",
    )
    return any(p in t for p in patterns)
