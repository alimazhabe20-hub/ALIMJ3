# Auto-split part 18: nowruz_countdown
def nowruz_countdown() -> str:
    today = jdatetime.datetime.now().date()
    year = today.year if (today.month, today.day) < (1, 1) else today.year + 1
    # اگر هنوز به ۱ فروردین نرسیده‌ایم
    if today.month == 1 and today.day == 1:
        return "🎉 **امروز نوروز است! سال نو مبارک**"
    target = jdatetime.date(today.year + (0 if today.month < 1 or (today.month == 1 and today.day == 1) else 1), 1, 1)
    if today >= jdatetime.date(today.year, 1, 1) and not (today.month == 1 and today.day == 1):
        target = jdatetime.date(today.year + 1, 1, 1)
    days = (target - today).days
    return (
        f"🌸 **شمارش‌معکوس نوروز**\n\n"
        f"⏳ {pn(days)} روز تا ۱ فروردین {pn(target.year)}\n"
        f"📅 تحویل سال: ۱ فروردین {pn(target.year)}"
    )
