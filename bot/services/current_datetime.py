"""Reliable current date/time service for the AI tool router."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def current_datetime(timezone_name: str = "", relative_day: int = 0) -> str:
    """Return current (or relative) local date/time with Gregorian and optional Jalali/Hijri calendars.

    relative_day:
      0  = today
      1  = tomorrow
     -1  = yesterday
      n  = n days from today (clamped to a safe range)
    """
    from bot.config import config

    tz_name = (timezone_name or getattr(config, "TIMEZONE", None) or "Asia/Tehran").strip()
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz_name = getattr(config, "TIMEZONE", None) or "Asia/Tehran"
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz_name = "UTC"
            tz = ZoneInfo("UTC")

    try:
        offset_days = int(relative_day or 0)
    except (TypeError, ValueError):
        offset_days = 0
    # Keep the offset bounded so the tool cannot be abused for absurd ranges.
    offset_days = max(-30, min(30, offset_days))

    now = datetime.now(tz) + timedelta(days=offset_days)

    weekday = {
        0: "دوشنبه",
        1: "سه‌شنبه",
        2: "چهارشنبه",
        3: "پنجشنبه",
        4: "جمعه",
        5: "شنبه",
        6: "یکشنبه",
    }.get(now.weekday(), "")

    if offset_days == 0:
        day_label = "امروز"
        title = f"تاریخ و زمان دقیق فعلی ({tz_name}):"
    elif offset_days == 1:
        day_label = "فردا"
        title = f"تاریخ فردا ({tz_name}):"
    elif offset_days == 2:
        day_label = "پس‌فردا"
        title = f"تاریخ پس‌فردا ({tz_name}):"
    elif offset_days == -1:
        day_label = "دیروز"
        title = f"تاریخ دیروز ({tz_name}):"
    elif offset_days > 0:
        day_label = f"{offset_days} روز بعد"
        title = f"تاریخ {offset_days} روز بعد ({tz_name}):"
    else:
        day_label = f"{abs(offset_days)} روز قبل"
        title = f"تاریخ {abs(offset_days)} روز قبل ({tz_name}):"

    lines = [
        title,
        f"برچسب: {day_label}",
        f"میلادی: {now.strftime('%Y-%m-%d')} — {weekday} — {now.strftime('%H:%M:%S')}",
    ]

    # Calendar conversions are enrichment only; the real system clock above
    # remains available even if an optional calendar package is unavailable.
    try:
        import jdatetime

        jalali = jdatetime.datetime.fromgregorian(datetime=now)
        lines.append(f"شمسی: {jalali.strftime('%Y/%m/%d')} — {weekday}")
    except Exception:
        pass

    try:
        from hijri_converter import Gregorian

        hijri = Gregorian(now.year, now.month, now.day).to_hijri()
        lines.append(f"قمری: {hijri.year}/{hijri.month:02d}/{hijri.day:02d}")
    except Exception:
        pass

    offset = now.strftime("%z")
    if len(offset) == 5:
        offset = f"{offset[:3]}:{offset[3:]}"
    lines.append(f"منطقه زمانی: {tz_name} ({offset})")
    lines.append(
        "توجه: این مقدار از ساعت واقعی سیستم گرفته شده و نباید با دانش قدیمی مدل جایگزین شود."
    )
    return "\n".join(lines)
