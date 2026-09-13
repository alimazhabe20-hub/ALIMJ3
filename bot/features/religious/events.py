"""
مناسبت‌های مذهبی و قمری — معماری هم‌تراز با تقویم (bot/api/calendar.py + bot/utils/events.py)

از getterهای مشترک get_hijri_events استفاده می‌کند تا منبع حقیقت واحد باشد
و نمایش ساختاریافته (امروز / آینده نزدیک / ماه جاری) ارائه دهد.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Tuple, Optional

try:
    import jdatetime
except ImportError:  # optional runtime fallback for stripped environments
    jdatetime = None
import pytz
try:
    from hijri_converter import Gregorian
except ImportError:  # optional dependency; functions degrade to empty/unknown dates
    Gregorian = None

from bot.config import config
from bot.utils.events import get_hijri_events

tehran_tz = pytz.timezone(config.TIMEZONE)

HIJRI_MONTH_NAMES = {
    1: "محرم", 2: "صفر", 3: "ربیع‌الاول", 4: "ربیع‌الثانی",
    5: "جمادی‌الاول", 6: "جمادی‌الثانی", 7: "رجب", 8: "شعبان",
    9: "رمضان", 10: "شوال", 11: "ذی‌قعده", 12: "ذی‌الحجه",
}


def _to_shamsi_str(gregorian_date) -> str:
    try:
        if jdatetime is not None:
            jd = jdatetime.date.fromgregorian(date=gregorian_date)
            return f"{jd.year}/{jd.month:02d}/{jd.day:02d}"
        # Dependency-free Gregorian -> Jalali fallback.
        gy, gm, gd = gregorian_date.year, gregorian_date.month, gregorian_date.day
        gdm = [0,31,59,90,120,151,181,212,243,273,304,334]
        gy2 = gy + 1 if gm > 2 else gy
        days = 355666 + 365*gy + (gy2+3)//4 - (gy2+99)//100 + (gy2+399)//400 + gd + gdm[gm-1]
        jy = -1595 + 33*(days//12053)
        days %= 12053
        jy += 4*(days//1461); days %= 1461
        if days > 365:
            jy += (days-1)//365; days = (days-1)%365
        if days < 186:
            jm = 1 + days//31; jd = 1 + days%31
        else:
            jm = 7 + (days-186)//30; jd = 1 + (days-186)%30
        return f"{jy}/{jm:02d}/{jd:02d}"
    except Exception:
        return str(gregorian_date)


def _hijri_label(hijri) -> str:
    month_name = HIJRI_MONTH_NAMES.get(hijri.month, str(hijri.month))
    return f"{hijri.day} {month_name} {hijri.year}"


def _events_for_gregorian(g_date) -> List[str]:
    """مناسبت‌های قمری یک روز میلادی — دقیقاً از منبع مشترک تقویم."""
    try:
        h = Gregorian(g_date.year, g_date.month, g_date.day).to_hijri()
        return get_hijri_events(h.month, h.day)
    except Exception:
        return []


def get_today_religious_events() -> List[Tuple[str, str, str]]:
    """
    مناسبت‌های امروز.
    برمی‌گرداند لیست (نام, قمری_label, شمسی)
    """
    now = datetime.now(tehran_tz).date()
    names = _events_for_gregorian(now)
    if not names:
        return []
    try:
        h = Gregorian(now.year, now.month, now.day).to_hijri()
        q_label = _hijri_label(h)
    except Exception:
        q_label = "—"
    shamsi = _to_shamsi_str(now)
    return [(name, q_label, shamsi) for name in names]


def get_upcoming_religious_events(days: int = 30, limit: int = 25) -> List[Tuple[int, str, str, str]]:
    """
    مناسبت‌های از امروز تا `days` روز آینده.
    خروجی: (offset_روز, نام, قمری_label, شمسی)
    اولین وقوع هر نام در بازه نگه‌داشته می‌شود.
    """
    today = datetime.now(tehran_tz).date()
    found: List[Tuple[int, str, str, str]] = []
    seen = set()

    for offset in range(0, max(1, days) + 1):
        target = today + timedelta(days=offset)
        names = _events_for_gregorian(target)
        if not names:
            continue
        try:
            h = Gregorian(target.year, target.month, target.day).to_hijri()
            q_label = _hijri_label(h)
        except Exception:
            q_label = "—"
        shamsi = _to_shamsi_str(target)
        for name in names:
            key = name.strip()
            if not key or key in seen:
                continue
            seen.add(key)
            found.append((offset, key, q_label, shamsi))
            if len(found) >= limit:
                return found
    return found


def get_month_religious_events(hijri_year: Optional[int] = None, hijri_month: Optional[int] = None) -> List[Tuple[int, str, str]]:
    """
    مناسبت‌های یک ماه قمری مشخص (پیش‌فرض: ماه جاری قمری).
    خروجی: (روز_قمری, نام, قمری_label)
    """
    today = datetime.now(tehran_tz).date()
    try:
        today_h = Gregorian(today.year, today.month, today.day).to_hijri()
    except Exception:
        return []

    year = hijri_year or today_h.year
    month = hijri_month or today_h.month
    results = []
    # حداکثر ۳۰ روز برای ماه‌های قمری
    for day in range(1, 31):
        names = get_hijri_events(month, day)
        if not names:
            continue
        label = f"{day} {HIJRI_MONTH_NAMES.get(month, month)} {year}"
        for name in names:
            results.append((day, name, label))
    return results


def religious_countdown(days: int = 30) -> str:
    """
    نمایش اصلی منوی «مناسبت مذهبی» — ساختاریافته مثل تقویم:
    - امروز
    - نزدیک‌ترین مناسبت‌ها در بازه
    """
    today = datetime.now(tehran_tz).date()
    try:
        today_h = Gregorian(today.year, today.month, today.day).to_hijri()
        today_q = _hijri_label(today_h)
    except Exception:
        today_q = "نامشخص"

    lines = [
        "🕌 **مناسبت‌های مذهبی و قمری**",
        f"امروز قمری: {today_q}",
        f"امروز شمسی: {_to_shamsi_str(today)}",
        "",
    ]

    today_events = get_today_religious_events()
    if today_events:
        lines.append("📌 **امروز:**")
        for name, q_label, _ in today_events:
            lines.append(f"• {name}")
        lines.append("")

    upcoming = get_upcoming_religious_events(days=days, limit=20)
    # فقط آینده (offset > 0) را در بخش جداگانه نشان بده
    future = [u for u in upcoming if u[0] > 0]
    if future:
        lines.append(f"📅 **نزدیک‌ترین مناسبت‌ها (تا {days} روز):**")
        for offset, name, q_label, shamsi in future:
            lines.append(
                f"• **{name}** — {offset} روز دیگر\n"
                f"  قمری: {q_label} | شمسی: {shamsi}"
            )
    elif not today_events:
        lines.append("مناسبت قمری ثبت‌شده‌ای در بازه فعلی یافت نشد.")

    return "\n".join(lines)


def religious_month_view() -> str:
    """نمای ماه جاری قمری — شبیه تقویم ماهانه."""
    today = datetime.now(tehran_tz).date()
    try:
        h = Gregorian(today.year, today.month, today.day).to_hijri()
    except Exception:
        return "خطا در محاسبه تاریخ قمری."

    month_name = HIJRI_MONTH_NAMES.get(h.month, str(h.month))
    events = get_month_religious_events(h.year, h.month)
    lines = [
        f"🕌 **مناسبت‌های ماه {month_name} {h.year}**",
        "",
    ]
    if not events:
        lines.append("مناسبتی برای این ماه ثبت نشده است.")
        return "\n".join(lines)

    by_day: dict[int, list[str]] = {}
    for day, name, _ in events:
        by_day.setdefault(day, []).append(name)

    for day in sorted(by_day.keys()):
        mark = " ← امروز" if day == h.day else ""
        names = "، ".join(by_day[day])
        lines.append(f"• روز {day}: {names}{mark}")

    return "\n".join(lines)
