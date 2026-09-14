# Auto-split part 15: convert_with_weekday
def convert_with_weekday(kind, y, m, d) -> str:
    try:
        if kind == "shamsi":
            j = jdatetime.date(y, m, d)
            g = j.togregorian()
            h = _g2h(g)
        elif kind == "gregorian":
            g = date(y, m, d)
            j = jdatetime.date.fromgregorian(date=g)
            h = _g2h(g)
        else:
            hh = Hijri(y, m, d)
            gg = hh.to_gregorian()
            g = date(gg.year, gg.month, gg.day)
            j = jdatetime.date.fromgregorian(date=g)
            h = {"day": d, "month": m, "month_name": HIJRI_MONTHS.get(m, str(m)), "year": y}
        wd = PERSIAN_WEEKDAYS[j.weekday()]
        j_num = f"{pn(j.year)}/{pn(f'{j.month:02d}')}/{pn(f'{j.day:02d}')}"
        g_num = f"{g.year}/{g.month:02d}/{g.day:02d}"
        hm = pn(f"{h['month']:02d}")
        hd = pn(f"{h['day']:02d}")
        h_num = f"{pn(h['year'])}/{hm}/{hd}"
        return (
            f"✅ **تبدیل تاریخ**\n\n"
            f"📅 شمسی: {wd} {pn(j.day)} {PERSIAN_MONTHS[j.month]} {pn(j.year)}  ({j_num})\n"
            f"📆 میلادی: {g.strftime('%A')} {g.day} {GREGORIAN_MONTHS[g.month]} {g.year}  ({g_num})\n"
            f"🌙 قمری: {pn(h['day'])} {h['month_name']} {pn(h['year'])}  ({h_num})"
        )
    except Exception:
        return "❌ تاریخ نامعتبر.\nمثال: `1403/05/18` یا `2024/08/09`"
