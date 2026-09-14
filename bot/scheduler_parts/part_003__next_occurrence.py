from datetime import datetime

# Auto-split part 3: _next_occurrence
def _next_occurrence(when: datetime, repeat_type: str, repeat_every: int) -> datetime | None:
    """محاسبه زمان بعدی برای یادآوری تکراری."""
    rt = (repeat_type or "once").lower()
    if rt in ("once", "", "none"):
        return None
    if rt == "daily":
        return when + timedelta(days=max(1, repeat_every or 1))
    if rt == "weekly":
        return when + timedelta(weeks=max(1, repeat_every or 1))
    if rt == "monthly":
        # تقریبی ۳۰ روز
        return when + timedelta(days=30 * max(1, repeat_every or 1))
    if rt in ("every_minutes", "minutes", "minutely"):
        mins = max(1, int(repeat_every or 1))
        return when + timedelta(minutes=mins)
    if rt in ("every_hours", "hours", "hourly"):
        hrs = max(1, int(repeat_every or 1))
        return when + timedelta(hours=hrs)
    return None
