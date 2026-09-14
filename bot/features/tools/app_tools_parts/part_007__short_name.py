# Auto-split part 7: _short_name
def _short_name(display_name: str, place_hint: str = "") -> str:
    if not display_name:
        return place_hint or "?"
    parts = [p.strip() for p in str(display_name).split(",") if p.strip()]
    if not parts:
        return place_hint or "?"
    skip = ("بخش", "شهرستان", "استان", "دهستان", "روستا", "county", "province",
            "district", "village", "region", "oblast", "governorate", "municipality")
    cleaned = []
    for p in parts:
        low = p.lower()
        if any(sw in low for sw in skip):
            continue
        if re.match(r"^[\d\s\-]+$", p):
            continue
        cleaned.append(p)
    if not cleaned:
        cleaned = parts[:2]
    if len(cleaned) >= 2:
        return f"{cleaned[0]}، {cleaned[-1]}"
    return cleaned[0]
