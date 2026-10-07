"""Reliable current date/time service for the AI tool router."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo


def current_datetime(timezone_name: str = "") -> str:
    """Return current local date/time with Gregorian and optional Jalali/Hijri calendars."""
    from bot.config import config

    tz_name = (timezone_name or config.TIMEZONE or "Asia/Tehran").strip()
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz_name = config.TIMEZONE or "Asia/Tehran"
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz_name = "UTC"
            tz = ZoneInfo("UTC")

    now = datetime.now(tz)
    weekday = {
        0: "دوشنبه", 1: "سه‌شنبه", 2: "چهارشنبه", 3: "پنجشنبه",
        4: "جمعه", 5: "شنبه", 6: "یکشنبه",
    }.get(now.weekday(), "")

    lines = [
        f"تاریخ و زمان دقیق فعلی ({tz_name}):",
        f"میلادی: {now.strftime('%Y-%m-%d')} — {weekday} — {now.strftime('%H:%M:%S')}",
    ]

    # Calendar conversions are enrichment only; the real system clock above
    # remains available even if an optional calendar package is unavailable.
    try:
        import jdatetime
        jalali = jdatetime.datetime.fromgregorian(datetime=now)
        lines.append(f"شمسی: {jalali.strftime('%Y/%m/%d')}")
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
    return "\n".join(lines)
