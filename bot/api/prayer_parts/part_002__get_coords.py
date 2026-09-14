# Auto-split part 2: _get_coords
def _get_coords(city: str):
    """برگرداندن (lat, lon) اگر موجود باشد، در غیر این صورت None"""
    if not city:
        return CITY_COORDS.get("قم")
    # جستجوی مستقیم با نام اصلی
    if city.strip() in CITY_COORDS:
        return CITY_COORDS[city.strip()]
    # جستجوی نرمال‌شده
    key = _normalize_city(city)
    if key in CITY_COORDS:
        return CITY_COORDS[key]
    return None
