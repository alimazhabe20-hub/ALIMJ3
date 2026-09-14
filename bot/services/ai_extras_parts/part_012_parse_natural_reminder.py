from datetime import datetime
from typing import Optional
from typing import Tuple

# Auto-split part 12: parse_natural_reminder
def parse_natural_reminder(text: str) -> Optional[Tuple[str, datetime, str, int]]:
    """Parse common Persian natural-language reminders.

    Returns: (body, when, repeat_type, repeat_every).
    Supports Persian/Arabic digits and one-time/daily/weekly/monthly/minute/hour repeats.
    """
    t = (text or "").strip()
    if not t:
        return None

    digit_map = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    t = t.translate(digit_map)
    normalized = t.replace("‌", " ")

    reminder_hint = re.search(
        r"یادآوری|یادم\s*(?:بیار|باشه|بنداز)|یادآوری\s*کن|ریمایندر|آلارم|خبرم\s*کن|پیام\s*بده|یاد\s*بده",
        normalized, re.I,
    )
    # مهم: صرفِ وجود زمان («فردا»، «ساعت ۹»، ...) به معنی درخواست یادآوری نیست.
    # این شرط جلوی تبدیل درخواست‌هایی مثل «فردا هوا قم چطوره؟» به Reminder را می‌گیرد.
    # فقط وقتی وارد parser می‌شویم که کاربر صریحاً قصد یادآوری/اطلاع‌رسانی زمان‌بندی‌شده را
    # بیان کرده باشد.
    if not reminder_hint:
        return None

    now = datetime.now(TEHRAN)
    when: Optional[datetime] = None
    repeat_type = "once"
    repeat_every = 0

    if re.search(r"هر\s*روز|روزانه|daily", normalized, re.I):
        repeat_type, repeat_every = "daily", 1
    elif re.search(r"هر\s*هفته|هفتگی|weekly", normalized, re.I):
        repeat_type, repeat_every = "weekly", 1
    elif re.search(r"هر\s*ماه|ماهانه|monthly", normalized, re.I):
        repeat_type, repeat_every = "monthly", 1
    else:
        m = re.search(r"هر\s*(\d+)\s*دقیقه", normalized, re.I)
        if m:
            repeat_type, repeat_every = "every_minutes", max(1, int(m.group(1)))
        else:
            m = re.search(r"هر\s*(\d+)\s*ساعت", normalized, re.I)
            if m:
                repeat_type, repeat_every = "every_hours", max(1, int(m.group(1)))

    def _hm() -> Optional[tuple[int, int]]:
        m = re.search(r"ساعت\s*(\d{1,2})(?:\s*[:：]\s*(\d{1,2}))?", normalized, re.I)
        if not m:
            return None
        return min(23, int(m.group(1))), min(59, int(m.group(2) or 0))

    m = re.search(r"(\d+)\s*دقیقه\s*(?:دیگه|دیگر)", normalized, re.I)
    if m:
        when = now + timedelta(minutes=max(1, int(m.group(1))))

    if when is None:
        m = re.search(r"(\d+)\s*ساعت\s*(?:دیگه|دیگر)", normalized, re.I)
        if m:
            when = now + timedelta(hours=max(1, int(m.group(1))))

    if when is None and re.search(r"پس\s*فردا", normalized, re.I):
        hm = _hm() or (9, 0)
        when = (now + timedelta(days=2)).replace(hour=hm[0], minute=hm[1], second=0, microsecond=0)

    if when is None and re.search(r"فردا", normalized, re.I):
        hm = _hm() or (9, 0)
        when = (now + timedelta(days=1)).replace(hour=hm[0], minute=hm[1], second=0, microsecond=0)

    if when is None:
        hm = _hm()
        if hm:
            when = now.replace(hour=hm[0], minute=hm[1], second=0, microsecond=0)
            if when <= now:
                when += timedelta(days=1)

    if when is None and repeat_type == "every_minutes":
        when = now + timedelta(minutes=repeat_every)
    elif when is None and repeat_type == "every_hours":
        when = now + timedelta(hours=repeat_every)
    elif when is None and repeat_type != "once":
        when = now + timedelta(minutes=1)

    if when is None:
        return None

    body = normalized
    body = re.sub(r"یادآوری(?:\s*کن)?|یادم\s*(?:بیار|باشه|بنداز)|ریمایندر|آلارم|خبرم\s*کن|یاد\s*بده", "", body, flags=re.I)
    body = re.sub(
        r"(?:\d+\s*دقیقه\s*(?:دیگه|دیگر)|\d+\s*ساعت\s*(?:دیگه|دیگر)|فردا|پس\s*فردا|امروز|ساعت\s*\d{1,2}(?:\s*[:：]\s*\d{1,2})?|هر\s*روز|روزانه|هر\s*هفته|هفتگی|هر\s*ماه|ماهانه|هر\s*\d+\s*دقیقه|هر\s*\d+\s*ساعت|daily|weekly|monthly)",
        "", body, flags=re.I,
    )
    body = re.sub(r"\s+", " ", body).strip(" :،,-") or "یادآوری"
    return body[:200], when, repeat_type, repeat_every
