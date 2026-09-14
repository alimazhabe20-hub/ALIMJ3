# Auto-split part 8: religious_month_view
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
