# Auto-split part 7: zodiac_animal
def zodiac_animal(y, m, d) -> str:
    try:
        j = jdatetime.date(y, m, d)
        g = j.togregorian()
        zodiac = "نامشخص"
        for m1, d1, m2, d2, name in ZODIAC:
            if (g.month == m1 and g.day >= d1) or (g.month == m2 and g.day <= d2):
                zodiac = name
                break
        animal = CHINESE_ANIMALS[(y - 1399) % 12]  # 1403=اژدها، 1404=مار
        return (
            f"♈ **برج و حیوان سال**\n\n"
            f"📅 {pn(d)} {PERSIAN_MONTHS[m]} {pn(y)}\n"
            f"📆 {g.day} {GREGORIAN_MONTHS[g.month]} {g.year}\n\n"
            f"✨ برج فلکی: {zodiac}\n🐾 حیوان سال: {animal}"
        )
    except Exception:
        return "❌ تاریخ نامعتبر.\nمثال: `1375/03/15`"
