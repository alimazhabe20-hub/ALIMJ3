# Auto-split part 12: birthday_countdown
def birthday_countdown(year: int, month: int, day: int) -> str:
    """چند روز تا تولد بعدی + سن بعدی"""
    try:
        now_j = jdatetime.datetime.now(tehran_tz)
        today = now_j.date()

        # تولد امسال
        try:
            this_year_bd = jdatetime.date(today.year, month, day)
        except ValueError:
            # ۲۹ اسفند در سال غیرکبیسه
            this_year_bd = jdatetime.date(today.year, month, day - 1)

        if this_year_bd >= today:
            next_bd = this_year_bd
            next_age = today.year - year
        else:
            try:
                next_bd = jdatetime.date(today.year + 1, month, day)
            except ValueError:
                next_bd = jdatetime.date(today.year + 1, month, day - 1)
            next_age = today.year - year + 1

        delta = next_bd - today
        days_left = delta.days

        current_age = today.year - year
        if (today.month, today.day) < (month, day):
            current_age -= 1

        if days_left == 0:
            status = "🎉 **امروز تولد شماست! تولدت مبارک**"
        else:
            status = f"⏳ **{to_persian_num(days_left)} روز** تا تولد بعدی"

        return (
            f"🎂 **روزشمار تولد**\n\n"
            f"📅 تاریخ تولد: {to_persian_num(day)} {PERSIAN_MONTHS[month]} {to_persian_num(year)}\n"
            f"🗓 سن فعلی: {to_persian_num(current_age)} سال\n\n"
            f"{status}\n"
            f"🎈 در تاریخ {to_persian_num(next_bd.day)} {PERSIAN_MONTHS[next_bd.month]} "
            f"{to_persian_num(next_bd.year)} → {to_persian_num(next_age)} ساله می‌شوید"
        )
    except Exception:
        return "❌ تاریخ نامعتبر است.\nمثال: `1375/03/15`"
