"""utils_events: calendar_data responsibilities."""
from .utils_events_common import *  # noqa: F401,F403
from . import utils_events_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


def get_international_shamsi_events(persian_year):
    """Return fixed-date international/world days for a Persian year."""
    first_gregorian_year = persian_year + 621
    result = {}

    for gy in (first_gregorian_year, first_gregorian_year + 1):
        for (gm, gd), names in INTERNATIONAL_DAYS_GREGORIAN.items():
            # Persian year starts around March 20/21.
            if gy == first_gregorian_year and gm < 3:
                continue
            if gy == first_gregorian_year + 1 and gm > 3:
                continue

            jy, jm, jd = _gregorian_to_jalali(gy, gm, gd)
            if jy != persian_year:
                continue

            key = f"{jm}-{jd}"
            result.setdefault(key, []).extend(names)

    return result

def get_shamsi_events(month: int, day: int) -> list[str]:
    """Return Persian-calendar events for a month/day pair."""
    try:
        key = f"{int(month)}-{int(day)}"
    except (TypeError, ValueError):
        return []
    return list(shamsi_events.get(key, ()))

def get_hijri_events(month: int, day: int) -> list[str]:
    """Return Hijri events for a month/day pair."""
    try:
        key = f"{int(month)}-{int(day)}"
    except (TypeError, ValueError):
        return []
    return list(hijri_events.get(key, ()))

def merge_international_shamsi_events(persian_year=1405):
    """Return a copy of shamsi_events with international days merged in."""
    merged = {key: list(values) for key, values in shamsi_events.items()}
    for key, names in get_international_shamsi_events(persian_year).items():
        bucket = merged.setdefault(key, [])
        for name in names:
            if name not in bucket:
                bucket.append(name)
    return merged
