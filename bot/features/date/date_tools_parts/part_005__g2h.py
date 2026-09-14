from datetime import date

# Auto-split part 5: _g2h
def _g2h(g: date) -> dict:
    try:
        # بدون هک یک‌روزه
        h = Gregorian(g.year, g.month, g.day).to_hijri()
        return {"day": h.day, "month": h.month, "month_name": HIJRI_MONTHS.get(h.month, str(h.month)), "year": h.year}
    except Exception:
        return {"day": 0, "month": 0, "month_name": "—", "year": 0}
