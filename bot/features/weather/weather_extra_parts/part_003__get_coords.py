# Auto-split part 3: _get_coords
def _get_coords(city: str):
    c = _norm_city(city)
    if c in CITY_COORDS:
        return CITY_COORDS[c]
    # جستجوی جزئی
    for k, v in CITY_COORDS.items():
        if c in k or k in c:
            return v
    return None
