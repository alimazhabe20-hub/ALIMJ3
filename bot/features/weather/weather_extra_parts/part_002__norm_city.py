# Auto-split part 2: _norm_city
def _norm_city(city: str) -> str:
    c = (city or "").strip().replace("ي", "ی").replace("ك", "ک")
    return c
