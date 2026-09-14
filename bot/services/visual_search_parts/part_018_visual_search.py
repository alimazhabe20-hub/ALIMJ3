# Auto-split part 18: visual_search
async def visual_search(
    image_bytes: bytes,
    caption: str = "",
    *,
    include_web: bool = True,
) -> str:
    """Analyze an image locally and return Lens-like ranked similar results."""
    if not image_bytes:
        return "❌ تصویر دریافت نشد."

    info = _image_info(image_bytes)
    ocr = await asyncio.to_thread(_ocr, image_bytes)
    vision = await asyncio.to_thread(_vision_caption, image_bytes)
    description = " ".join(x for x in (vision, caption) if x).strip()
    keywords = _extract_keywords(" ".join(x for x in (vision, ocr, caption) if x))

    results: list[SearchResult] = []
    queries = _query_variants(description, ocr, caption)
    if include_web and queries:
        batches = await asyncio.gather(*(_ddg_search(q) for q in queries), return_exceptions=True)
        for batch in batches:
            if isinstance(batch, list):
                results.extend(batch)
    ranked = _dedupe_and_rank(results, description, ocr, caption)

    lines = ["🔎 تحلیل تصویری / Visual Lens", ""]
    if info:
        lines.append(f"📐 تصویر: {info.get('width')}×{info.get('height')} | {info.get('format', '')}")
    if vision:
        lines.append(f"👁️ تشخیص مدل: {vision[:500]}")
    if ocr:
        lines.append(f"📝 متن داخل تصویر: {ocr[:700]}")
    if keywords:
        lines.append("🔑 کلیدواژه‌ها: " + "، ".join(keywords[:12]))

    if queries:
        lines.append("\n🔍 جستجوهای ساخته‌شده:")
        lines.extend(f"• {q}" for q in queries[:MAX_QUERIES])

    lines.append("")
    if ranked:
        lines.append("🛍️ نزدیک‌ترین نتایج پیدا شده (نیازی به تطابق ۱۰۰٪ نیست):")
        for i, r in enumerate(ranked[:8], 1):
            pct = round(r.score * 100)
            lines.append(f"\n{i}. ⭐ {pct}% — {r.title[:180]}\n{r.url}")
            if r.snippet:
                lines.append(f"   {r.snippet[:260]}")
    else:
        lines.append("ℹ️ نتیجه دقیق پیدا نشد؛ جستجوی وب نتیجه قابل اتکایی برنگرداند.")
        lines.append("💡 اگر عکس واضح‌تر یا نمای نزدیک‌تر بفرستید، شانس پیدا کردن مشابه بیشتر می‌شود.")

    lines.append("\n⚠️ درصدها «شباهت تقریبی متنی/جستجویی» هستند، نه تضمین تطابق محصول.")
    return "\n".join(lines)[:12000]
