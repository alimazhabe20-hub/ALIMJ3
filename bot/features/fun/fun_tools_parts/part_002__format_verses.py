# Auto-split part 2: _format_verses
def _format_verses(verses: list) -> str:
    """چیدمان ابیات مثل سایت‌های فال حافظ (مصراع‌ها جفت‌جفت)"""
    lines = []
    couplet = []
    for v in verses:
        if not isinstance(v, dict):
            continue
        text = (v.get("text") or "").strip()
        if not text:
            continue
        couplet.append(text)
        # versePosition 0 = مصراع اول، 1 = مصراع دوم
        pos = v.get("versePosition")
        if pos == 1 or len(couplet) >= 2:
            lines.append("\n".join(couplet))
            couplet = []
    if couplet:
        lines.append("\n".join(couplet))
    return "\n\n".join(lines)
