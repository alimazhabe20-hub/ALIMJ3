# Auto-split part 14: date_diff
def date_diff(y1, m1, d1, y2, m2, d2, kind="shamsi") -> str:
    """فاصله بین دو تاریخ شمسی"""
    try:
        if kind == "shamsi":
            a = jdatetime.date(y1, m1, d1)
            b = jdatetime.date(y2, m2, d2)
        else:
            a = jdatetime.date.fromgregorian(date=date(y1, m1, d1))
            b = jdatetime.date.fromgregorian(date=date(y2, m2, d2))

        if a > b:
            a, b = b, a
            y1, m1, d1, y2, m2, d2 = y2, m2, d2, y1, m1, d1

        delta = b - a
        total_days = delta.days

        years = b.year - a.year
        months = b.month - a.month
        days = b.day - a.day
        if days < 0:
            months -= 1
            prev_m = b.month - 1 if b.month > 1 else 12
            prev_y = b.year if b.month > 1 else b.year - 1
            days += jdatetime.date(prev_y, prev_m, 1).daysinmonth
        if months < 0:
            years -= 1
            months += 12

        weeks = total_days // 7

        return (
            f"📅 **اختلاف دو تاریخ**\n\n"
            f"از: {to_persian_num(d1)} {PERSIAN_MONTHS.get(m1, m1)} {to_persian_num(y1)}\n"
            f"تا: {to_persian_num(d2)} {PERSIAN_MONTHS.get(m2, m2)} {to_persian_num(y2)}\n\n"
            f"🗓 **{to_persian_num(years)}** سال و **{to_persian_num(months)}** ماه و **{to_persian_num(days)}** روز\n"
            f"📆 مجموع: **{to_persian_num(f'{total_days:,}')}** روز\n"
            f"🗓 حدود **{to_persian_num(weeks)}** هفته"
        )
    except Exception:
        return (
            "❌ تاریخ نامعتبر است.\n"
            "فرمت: `1375/03/15 1403/05/18`\n"
            "(دو تاریخ شمسی با فاصله)"
        )
