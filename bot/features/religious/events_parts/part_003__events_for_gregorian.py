from typing import List

# Auto-split part 3: _events_for_gregorian
def _events_for_gregorian(g_date) -> List[str]:
    """مناسبت‌های قمری یک روز میلادی — دقیقاً از منبع مشترک تقویم."""
    try:
        h = Gregorian(g_date.year, g_date.month, g_date.day).to_hijri()
        return get_hijri_events(h.month, h.day)
    except Exception:
        return []
