# Auto-split part 2: _city_from_query
def _city_from_query(text: str) -> str | None:
    """Extract a likely city name; avoid swallowing the rest of a multi-intent sentence."""
    m = re.search(
        r"(?:هوای|آب\s*و\s*هوای|هوا(?:ی)?|weather(?:\s+in)?)\s+([\w\u0600-\u06ff]{2,24})",
        text,
        re.I,
    )
    if not m:
        return None
    value = m.group(1).strip(" ؟?!،,.:")
    stop = {"امروز", "فردا", "الان", "فعلی", "و", "قیمت", "دلار", "یورو", "طلا", "بازار"}
    if not value or value in stop:
        return None
    if any(tok in value for tok in (" و", " قیمت", " دلار")):
        return None
    return value
