# Auto-split part 13: lunar_age
def lunar_age(year: int, month: int, day: int) -> str:
    """سن قمری + تاریخ رسیدن به ۹ و ۱۵ سال قمری (سن تکلیف)"""
    try:
        birth_j = jdatetime.date(year, month, day)
        birth_g = birth_j.togregorian()
        h_birth = _gregorian_to_hijri(birth_g)

        now = datetime.now(tehran_tz)
        now_g = now.date()
        h_now = _gregorian_to_hijri(now_g)

        # سن قمری تقریبی (سال قمری ≈ ۳۵۴ روز)
        birth_h_approx = Hijri(h_birth["year"], h_birth["month"], min(h_birth["day"], 28))
        now_h_approx = Hijri(h_now["year"], h_now["month"], min(h_now["day"], 28))

        # محاسبه سال/ماه/روز قمری
        hy = h_now["year"] - h_birth["year"]
        hm = h_now["month"] - h_birth["month"]
        hd = h_now["day"] - h_birth["day"]
        if hd < 0:
            hm -= 1
            hd += 29  # تقریب ماه قمری
        if hm < 0:
            hy -= 1
            hm += 12

        # تاریخ رسیدن به ۹ و ۱۵ سال قمری
        taklif_9 = None
        taklif_15 = None
        try:
            h9 = Hijri(h_birth["year"] + 9, h_birth["month"], min(h_birth["day"], 28))
            g9 = h9.to_gregorian()
            j9 = jdatetime.date.fromgregorian(date=date(g9.year, g9.month, g9.day))
            taklif_9 = f"{to_persian_num(j9.day)} {PERSIAN_MONTHS[j9.month]} {to_persian_num(j9.year)}"
        except Exception:
            taklif_9 = "—"

        try:
            h15 = Hijri(h_birth["year"] + 15, h_birth["month"], min(h_birth["day"], 28))
            g15 = h15.to_gregorian()
            j15 = jdatetime.date.fromgregorian(date=date(g15.year, g15.month, g15.day))
            taklif_15 = f"{to_persian_num(j15.day)} {PERSIAN_MONTHS[j15.month]} {to_persian_num(j15.year)}"
        except Exception:
            taklif_15 = "—"

        return (
            f"🌙 **سن قمری و سن تکلیف**\n\n"
            f"📅 تولد شمسی: {to_persian_num(day)} {PERSIAN_MONTHS[month]} {to_persian_num(year)}\n"
            f"🌙 تولد قمری: {to_persian_num(h_birth['day'])} {h_birth['month_name']} {to_persian_num(h_birth['year'])}\n\n"
            f"🗓 **سن قمری:** {to_persian_num(hy)} سال و {to_persian_num(hm)} ماه و {to_persian_num(hd)} روز\n\n"
            f"👧 **سن تکلیف دختران (۹ قمری):** {taklif_9}\n"
            f"👦 **سن تکلیف پسران (۱۵ قمری):** {taklif_15}"
        )
    except Exception:
        return "❌ تاریخ نامعتبر است.\nمثال: `1375/03/15`"
