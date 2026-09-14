# Auto-split part 11: zodiac_and_animal
def zodiac_and_animal(year: int, month: int, day: int) -> str:
    """برج فلکی + حیوان سال تولد"""
    try:
        zodiac = get_zodiac_from_shamsi(year, month, day)
        animal = get_animal_year(year)
        j = jdatetime.date(year, month, day)
        g = j.togregorian()
        return (
            f"♈ **برج و حیوان سال تولد**\n\n"
            f"📅 تولد: {to_persian_num(day)} {PERSIAN_MONTHS[month]} {to_persian_num(year)}\n"
            f"📆 میلادی: {g.day} {GREGORIAN_MONTHS[g.month]} {g.year}\n\n"
            f"✨ **برج فلکی:** {zodiac}\n"
            f"🐾 **حیوان سال:** {animal}"
        )
    except Exception:
        return "❌ تاریخ نامعتبر است.\nمثال: `1375/03/15`"
