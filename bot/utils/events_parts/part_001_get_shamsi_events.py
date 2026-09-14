# Auto-split part 1: get_shamsi_events
def get_shamsi_events(month: int, day: int) -> list[str]:
    """Return Persian-calendar events for a month/day pair."""
    try:
        key = f"{int(month)}-{int(day)}"
    except (TypeError, ValueError):
        return []
    return list(shamsi_events.get(key, ()))
