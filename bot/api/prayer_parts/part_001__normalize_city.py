# Auto-split part 1: _normalize_city
def _normalize_city(city: str) -> str:
    """نرمال‌سازی نام شهر برای جستجو در دیکشنری مختصات"""
    if not city:
        return "قم"
    return city.strip().replace("ي", "ی").replace("ك", "ک").lower()
