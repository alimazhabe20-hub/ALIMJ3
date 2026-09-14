from typing import List
from typing import Tuple

# Auto-split part 5: get_upcoming_religious_events
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
