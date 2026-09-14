from typing import Optional

# Auto-split part 6: select_capability_tool
def select_capability_tool(prompt: str) -> Optional[str]:
    """انتخاب ابزار فقط وقتی تطبیق به‌اندازه کافی قوی و غیرمبهم باشد.

    امتیازدهی چندمرحله‌ای است: عبارت‌های بلندتر و تطبیق‌های چندکلمه‌ای وزن بیشتری
    دارند. اگر دو قابلیت هم‌زمان امتیاز نزدیک داشته باشند، هیچ ابزاری به‌صورت اجباری
    انتخاب نمی‌شود تا مدل بتواند درخواست چندبخشی را با چند Tool مدیریت کند.
    """
    text = _normalize_capability_text(prompt)
    if not text:
        return None

    ranked = []
    for name, entry in _REGISTRY.items():
        score = 0.0
        hits = 0
        longest = 0
        for kw in entry.get("keywords") or []:
            try:
                m = re.search(kw, text, re.I)
            except re.error:
                continue
            if not m:
                continue
            matched = (m.group(0) or kw).strip()
            length = len(re.sub(r"\\s+", "", matched))
            # تطبیق‌های مشخص‌تر از keywordهای عمومی مثل «قیمت» مهم‌ترند.
            score += 1.0 + min(length, 64) / 16.0
            hits += 1
            longest = max(longest, length)

        if not hits:
            continue
        if name == "run_agent" and score < 2.0:
            continue
        ranked.append((score, hits, longest, name))

    if not ranked:
        return None

    ranked.sort(reverse=True)
    best = ranked[0]
    if len(ranked) > 1:
        second = ranked[1]
        # درخواست‌های چندقابلیتی را به یک Tool قفل نکن.
        if (best[0] < second[0] * 1.10 and
                best[2] <= second[2] + 2 and
                best[1] <= second[1] + 1):
            return None
        # اگر دو قابلیت متفاوت در یک درخواست با «و» حضور دارند، یک Tool را force نکن.
        if second[3] != best[3] and second[0] >= 1.25 and re.search(r"\sو\s", text):
            return None

    # تطبیق تک‌کلمه‌ای ضعیف، به‌تنهایی مجوز force کردن Tool نیست.
    if best[0] < 1.25 or (best[2] < 5 and len(text.split()) <= 1):
        return None
    if best[2] == 5 and len(text.split()) <= 1:
        return None
    return best[3]
