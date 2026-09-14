from typing import List
from typing import Optional
from typing import Tuple

# Auto-split part 6: get_month_religious_events
def get_month_religious_events(hijri_year: Optional[int] = None, hijri_month: Optional[int] = None) -> List[Tuple[int, str, str]]:
    """
    مناسبت‌های یک ماه قمری مشخص (پیش‌فرض: ماه جاری قمری).
    خروجی: (روز_قمری, نام, قمری_label)
    """
    today = datetime.now(tehran_tz).date()
    try:
        today_h = Gregorian(today.year, today.month, today.day).to_hijri()
    except Exception:
        return []

    year = hijri_year or today_h.year
    month = hijri_month or today_h.month
    results = []
    # حداکثر ۳۰ روز برای ماه‌های قمری
    for day in range(1, 31):
        names = get_hijri_events(month, day)
        if not names:
            continue
        label = f"{day} {HIJRI_MONTH_NAMES.get(month, month)} {year}"
        for name in names:
            results.append((day, name, label))
    return results
