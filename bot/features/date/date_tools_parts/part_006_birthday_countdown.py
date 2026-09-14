# Auto-split part 6: birthday_countdown
def birthday_countdown(y, m, d) -> str:
    try:
        today = jdatetime.datetime.now().date()
        try:
            this_bd = jdatetime.date(today.year, m, d)
        except ValueError:
            this_bd = jdatetime.date(today.year, m, d - 1)
        if this_bd >= today:
            next_bd, next_age = this_bd, today.year - y
        else:
            try:
                next_bd = jdatetime.date(today.year + 1, m, d)
            except ValueError:
                next_bd = jdatetime.date(today.year + 1, m, d - 1)
            next_age = today.year - y + 1
        days_left = (next_bd - today).days
        cur_age = today.year - y - (0 if (today.month, today.day) >= (m, d) else 1)
        status = "🎉 **امروز تولد شماست!**" if days_left == 0 else f"⏳ **{pn(days_left)} روز** تا تولد بعدی"
        return (
            f"🎂 **روزشمار تولد**\n\n"
            f"📅 تولد: {pn(d)} {PERSIAN_MONTHS[m]} {pn(y)}\n"
            f"🗓 سن فعلی: {pn(cur_age)} سال\n\n{status}\n"
            f"🎈 {pn(next_bd.day)} {PERSIAN_MONTHS[next_bd.month]} {pn(next_bd.year)} → {pn(next_age)} ساله"
        )
    except Exception:
        return "❌ تاریخ نامعتبر.\nمثال: `1375/03/15`"
