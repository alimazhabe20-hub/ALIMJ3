# Auto-split part 12: _query_variants
def _query_variants(query: str) -> list[str]:
    """ساخت چند جستجوی کوتاه‌تر تا نتیجه به تطابق لفظ‌به‌لفظ وابسته نباشد."""
    q = re.sub(r"\s+", " ", (query or "").strip())
    if not q:
        return []

    variants: list[str] = [q]
    # کلمات کم‌ارزش در توصیف‌های بینایی را حذف می‌کنیم.
    stop = {
        "یک", "عدد", "نوع", "مدل", "شکل", "طرح", "دارای", "با", "و", "از",
        "برای", "در", "روی", "رنگ", "مناسب", "دکوری", "دکوراتیو", "خاص",
        "برجستگی", "برجسته", "تصویر", "عکس",
    }
    words = [w for w in re.findall(r"[\wآ-ی]{2,}", q.lower()) if w not in stop]
    if words:
        variants.append(" ".join(words))
    if len(words) >= 4:
        # دو نسخه کوتاه برای موتور جستجو؛ یکی ابتدای توصیف و یکی انتهای آن.
        variants.append(" ".join(words[:4]))
        variants.append(" ".join(words[-4:]))
    # چند جایگزین رایج برای توصیف‌های فارسی/بازاری.
    synonym_groups = [
        ("چوب پنبه ای", "چوب پنبه"),
        ("چوب‌پنبه‌ای", "چوب پنبه"),
        ("چوبی", "درب چوبی"),
        ("شیشه ای", "شیشه"),
        ("شیشه‌ای", "شیشه"),
    ]
    for a, b in synonym_groups:
        if a in q.lower():
            variants.append(q.lower().replace(a, b))

    out: list[str] = []
    seen: set[str] = set()
    for v in variants:
        v = re.sub(r"\s+", " ", v).strip()
        if len(v) >= 4 and v not in seen:
            seen.add(v)
            out.append(v)
    return out[:6]
