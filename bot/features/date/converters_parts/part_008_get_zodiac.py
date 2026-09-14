# Auto-split part 8: get_zodiac
def get_zodiac(month: int, day: int) -> str:
    """برج فلکی بر اساس ماه و روز میلادی"""
    for m1, d1, m2, d2, name in ZODIAC:
        if (month == m1 and day >= d1) or (month == m2 and day <= d2):
            if m1 == m2 or (month == m1 and day >= d1) or (month == m2 and day <= d2):
                return name
    return "نامشخص"
