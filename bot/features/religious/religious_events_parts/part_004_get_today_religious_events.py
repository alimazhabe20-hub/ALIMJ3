from typing import List
from typing import Tuple

# Auto-split part 4: get_today_religious_events
def get_today_religious_events() -> List[Tuple[str, str, str]]:
    """
    مناسبت‌های امروز.
    برمی‌گرداند لیست (نام, قمری_label, شمسی)
    """
    now = datetime.now(tehran_tz).date()
    names = _events_for_gregorian(now)
    if not names:
        return []
    try:
        h = Gregorian(now.year, now.month, now.day).to_hijri()
        q_label = _hijri_label(h)
    except Exception:
        q_label = "—"
    shamsi = _to_shamsi_str(now)
    return [(name, q_label, shamsi) for name in names]
