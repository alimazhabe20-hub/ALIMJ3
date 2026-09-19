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

    # عبارت‌های طبیعی مثل «بیدارم کن» هم درخواست یادآوری هستند.
    # اما صرفِ وجود «فردا/ساعت...» نباید پیام عادی را Reminder کند.
    reminder_hint = re.search(
        r"یادآوری|یادم\s*(?:بیار|باشه|بنداز)|ریمایندر|آلارم|خبرم\s*کن|پیام\s*بده|یاد\s*بده|بیدارم\s*کن|منو\s*بیدار\s*کن|یادم\s*بنداز",
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

    number_words = {
        "صفر": 0, "یک": 1, "یه": 1, "دو": 2, "سه": 3, "چهار": 4,
        "پنج": 5, "شش": 6, "شیش": 6, "هفت": 7, "هشت": 8, "نه": 9,
        "ده": 10, "یازده": 11, "دوازده": 12, "سیزده": 13, "چهارده": 14,
        "پانزده": 15, "شانزده": 16, "هفده": 17, "هجده": 18, "نوزده": 19,
        "بیست": 20, "بیست و یک": 21, "بیست و دو": 22, "بیست و سه": 23,
    }

    def _hm() -> Optional[tuple[int, int]]:
        # «ساعت 9»، «ساعت 9:30»، «ساعت نه»، «ساعت نه و نیم»
        m = re.search(
            r"ساعت\s*(\d{1,2})(?:\s*[:：]\s*(\d{1,2}))?",
            normalized, re.I,
        )
        if m:
            hour = int(m.group(1))
            minute = int(m.group(2) or 0)
        else:
            word_pattern = "|".join(re.escape(k) for k in sorted(number_words, key=len, reverse=True))
            m = re.search(r"ساعت\s*(" + word_pattern + r")(?:\s*و\s*نیم)?", normalized, re.I)
            if not m:
                return None
            hour = number_words[m.group(1)]
            minute = 30 if "و نیم" in m.group(0) else 0

        # «صبح/بامداد» را صبح نگه می‌داریم و «ظهر/شب/عصر» را به ساعت 24 ساعته تبدیل می‌کنیم.
        context = normalized[m.end():m.end() + 12]
        if re.search(r"(?:صبح|بامداد)", context, re.I):
            if hour == 12:
                hour = 0
        elif re.search(r"(?:ظهر|عصر|شب)", context, re.I):
            if hour < 12:
                hour += 12
        return min(23, hour), min(59, minute)

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
        r"(?:\d+\s*دقیقه\s*(?:دیگه|دیگر)|\d+\s*ساعت\s*(?:دیگه|دیگر)|فردا|پس\s*فردا|امروز|ساعت\s*(?:\d{1,2}(?:\s*[:：]\s*\d{1,2})?|یک|یه|دو|سه|چهار|پنج|شش|شیش|هفت|هشت|نه|ده|یازده|دوازده|سیزده|چهارده|پانزده|شانزده|هفده|هجده|نوزده|بیست)(?:\s*و\s*نیم)?|(?:صبح|بامداد|ظهر|عصر|شب)|هر\s*روز|روزانه|هر\s*هفته|هفتگی|هر\s*ماه|ماهانه|هر\s*\d+\s*دقیقه|هر\s*\d+\s*ساعت|daily|weekly|monthly)",
        "", body, flags=re.I,
    )
    body = re.sub(r"\s+", " ", body).strip(" :،,-") or "یادآوری"
    return body[:200], when, repeat_type, repeat_every
