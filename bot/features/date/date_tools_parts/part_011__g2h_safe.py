# Auto-split part 11: _g2h_safe
def _g2h_safe(g):
    try:
        h = Gregorian(g.year, g.month, g.day).to_hijri()
        return h.year, h.month, h.day, HIJRI_MONTHS.get(h.month, str(h.month))
    except Exception:
        return None, None, None, "—"
