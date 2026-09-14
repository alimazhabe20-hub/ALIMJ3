# Auto-split part 2: get_hijri_events
def get_hijri_events(month: int, day: int) -> list[str]:
    """Return Hijri events for a month/day pair."""
    try:
        key = f"{int(month)}-{int(day)}"
    except (TypeError, ValueError):
        return []
    return list(hijri_events.get(key, ()))
