# Auto-split part 6: _norm_place
def _norm_place(s: str) -> str:
    s = (s or "").strip()
    s = s.replace("ي", "ی").replace("ك", "ک").replace("‌", " ").replace("  ", " ")
    return s.strip().lower()
