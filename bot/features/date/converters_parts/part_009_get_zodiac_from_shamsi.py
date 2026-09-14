# Auto-split part 9: get_zodiac_from_shamsi
def get_zodiac_from_shamsi(year: int, month: int, day: int) -> str:
    try:
        j = jdatetime.date(year, month, day)
        g = j.togregorian()
        return get_zodiac(g.month, g.day)
    except Exception:
        return "نامشخص"
