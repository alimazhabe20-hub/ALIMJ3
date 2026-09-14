# Auto-split part 7: religious_countdown
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
