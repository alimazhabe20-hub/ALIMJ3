from datetime import date

# Auto-split part 5: _gregorian_to_hijri
def _gregorian_to_hijri(g: date) -> dict:
    try:
        # بدون هک یک‌روزه — مطابق استاندارد و اکثر تقویم‌ها
        h = Gregorian(g.year, g.month, g.day).to_hijri()
        return {
            "day": h.day,
            "month": h.month,
            "month_name": HIJRI_MONTHS.get(h.month, str(h.month)),
            "year": h.year,
        }
    except Exception:
        return {"day": 0, "month": 0, "month_name": "نامشخص", "year": 0}
