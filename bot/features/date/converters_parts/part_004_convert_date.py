# Auto-split part 4: convert_date
def convert_date(kind: str, year: int, month: int, day: int) -> str:
    """تبدیل تاریخ به هر سه سیستم و برگرداندن متن فرمت‌شده"""
    try:
        if kind == "shamsi":
            j = jdatetime.date(year, month, day)
            g = j.togregorian()
            h_info = _gregorian_to_hijri(g)
        elif kind == "gregorian":
            g = date(year, month, day)
            j = jdatetime.date.fromgregorian(date=g)
            h_info = _gregorian_to_hijri(g)
        elif kind == "hijri":
            h = Hijri(year, month, day)
            g = h.to_gregorian()
            g = date(g.year, g.month, g.day)
            j = jdatetime.date.fromgregorian(date=g)
            h_info = {
                "day": day,
                "month": month,
                "month_name": HIJRI_MONTHS.get(month, str(month)),
                "year": year,
            }
        else:
            return "❌ نوع تاریخ نامعتبر است."

        shamsi_str = (
            f"{to_persian_num(j.day)} {PERSIAN_MONTHS[j.month]} "
            f"{to_persian_num(j.year)}  "
            f"({to_persian_num(j.year)}/{to_persian_num(f'{j.month:02d}')}/{to_persian_num(f'{j.day:02d}')})"
        )
        miladi_str = f"{g.day} {GREGORIAN_MONTHS[g.month]} {g.year}  ({g.year}/{g.month:02d}/{g.day:02d})"
        hy = to_persian_num(h_info["year"])
        hm = to_persian_num(f"{h_info['month']:02d}")
        hd = to_persian_num(f"{h_info['day']:02d}")
        hijri_str = (
            f"{to_persian_num(h_info['day'])} {h_info['month_name']} "
            f"{hy}  ({hy}/{hm}/{hd})"
        )

        return (
            f"✅ **نتیجه تبدیل تاریخ**\n\n"
            f"📅 **شمسی:** {shamsi_str}\n"
            f"📆 **میلادی:** {miladi_str}\n"
            f"🌙 **قمری:** {hijri_str}"
        )
    except Exception as e:
        return f"❌ تاریخ نامعتبر است.\nمثال: `1403/05/18` یا `2024/08/09` یا `15 صفر 1446`"
