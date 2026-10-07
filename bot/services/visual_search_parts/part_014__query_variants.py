# Auto-split part 14: _query_variants
def _query_variants(description: str, ocr: str, caption: str = "") -> list[str]:
    """Generate short, complementary queries instead of one overly-specific sentence."""
    text = " ".join(x for x in (description, caption, ocr) if x)
    keys = _extract_keywords(text, 16)
    if not keys:
        return []

    # Keep phrases around product nouns/visual attributes, but avoid a huge exact sentence.
    variants: list[str] = []
    base = " ".join(keys[:6])
    if base:
        variants.append(base)
    if len(keys) >= 3:
        variants.append(" ".join(keys[:3]) + " محصول")
        variants.append(" ".join(keys[:3]) + " خرید")
    if len(keys) >= 5:
        variants.append(" ".join(keys[:5]) + " فروشگاه")
        variants.append(" ".join(keys[1:6]))

    # English fallback can improve recall for globally indexed product pages.
    english_terms = [
        k for k in keys
        if re.fullmatch(r"[a-z0-9.-]+", k)
    ]
    if english_terms:
        variants.append(" ".join(english_terms[:6]) + " product")

    # Always have a broader query based on the first semantic terms.
    variants.append(" ".join(keys[:4]))
    return _unique(variants)[:MAX_QUERIES]
