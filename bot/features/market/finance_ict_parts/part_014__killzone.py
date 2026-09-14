from datetime import datetime

# Auto-split part 14: _killzone
def _killzone(now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    h, m = now.hour, now.minute
    t = h + m / 60.0
    # Approximate ICT windows in UTC (standard teaching, not DST-perfect)
    zones = [
        (0.0, 3.0, "Asia", "آسیا"),
        (7.0, 10.0, "London", "لندن"),
        (12.0, 15.0, "New York", "نیویورک AM"),
        (15.0, 17.0, "NY Lunch / overlap", "همپوشانی لندن–نیویورک"),
        (19.0, 22.0, "New York PM", "نیویورک PM"),
    ]
    active = []
    for a, b, en, fa in zones:
        if a <= t < b:
            active.append(fa)
    return {
        "utc": now.strftime("%H:%M UTC"),
        "active": active,
        "text": (
            "⏰ Killzone فعال: " + "، ".join(active)
            if active
            else f"⏰ خارج از Killzoneهای اصلی ({now.strftime('%H:%M')} UTC)"
        ),
    }
