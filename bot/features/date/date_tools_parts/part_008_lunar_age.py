# Auto-split part 8: lunar_age
def lunar_age(y, m, d) -> str:
    try:
        birth_g = jdatetime.date(y, m, d).togregorian()
        hb = _g2h(birth_g)
        hn = _g2h(datetime.now(tehran_tz).date())
        hy = hn["year"] - hb["year"]
        hm = hn["month"] - hb["month"]
        hd = hn["day"] - hb["day"]
        if hd < 0:
            hm -= 1
            hd += 29
        if hm < 0:
            hy -= 1
            hm += 12

        def taklif(add):
            try:
                h = Hijri(hb["year"] + add, hb["month"], min(hb["day"], 28))
                g = h.to_gregorian()
                j = jdatetime.date.fromgregorian(date=date(g.year, g.month, g.day))
                return f"{pn(j.day)} {PERSIAN_MONTHS[j.month]} {pn(j.year)}"
            except Exception:
                return "—"

        return (
            f"🌙 **سن قمری و سن تکلیف**\n\n"
            f"📅 شمسی: {pn(d)} {PERSIAN_MONTHS[m]} {pn(y)}\n"
            f"🌙 قمری: {pn(hb['day'])} {hb['month_name']} {pn(hb['year'])}\n\n"
            f"🗓 سن قمری: {pn(hy)} سال و {pn(hm)} ماه و {pn(hd)} روز\n\n"
            f"👧 سن تکلیف دختران (۹ق): {taklif(9)}\n"
            f"👦 سن تکلیف پسران (۱۵ق): {taklif(15)}"
        )
    except Exception:
        return "❌ تاریخ نامعتبر.\nمثال: `1375/03/15`"
