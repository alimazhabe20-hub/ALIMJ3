# Auto-split part 20: custom_countdown
def custom_countdown(y, m, d, label="رویداد") -> str:
    try:
        today = jdatetime.datetime.now().date()
        target = jdatetime.date(y, m, d)
        delta = (target - today).days
        if delta > 0:
            return f"⏳ **شمارش‌معکوس: {label}**\n\n{pn(delta)} روز مانده\n📅 {pn(d)} {PERSIAN_MONTHS[m]} {pn(y)}"
        if delta == 0:
            return f"🎉 **امروز همان روز است: {label}**"
        return f"📅 **{label}** {pn(abs(delta))} روز پیش بوده است."
    except Exception:
        return "❌ تاریخ نامعتبر.\nمثال: `1405/01/01 نوروز`"
