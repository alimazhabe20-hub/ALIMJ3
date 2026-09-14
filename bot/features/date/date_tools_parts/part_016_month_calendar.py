# Auto-split part 16: month_calendar
def month_calendar(year=None, month=None) -> str:
    try:
        today = jdatetime.datetime.now().date()
        year = year or today.year
        month = month or today.month
        first = jdatetime.date(year, month, 1)
        # jdatetime.j_days_in_month یک لیست است نه تابع
        days_in = jdatetime.j_days_in_month[month - 1]
        if month == 12 and jdatetime.date(year, 1, 1).isleap():
            days_in = 30
        start_wd = first.weekday()  # 0=شنبه
        lines = [f"📅 **{PERSIAN_MONTHS[month]} {pn(year)}**\n", "ش ی د س چ پ ج"]
        row = ["  "] * start_wd
        for day in range(1, days_in + 1):
            mark = f"{day:2d}"
            if day == today.day and month == today.month and year == today.year:
                mark = f"[{day}]"
            row.append(f"{mark:>3}")
            if len(row) == 7:
                lines.append(" ".join(row))
                row = []
        if row:
            lines.append(" ".join(row))
        # مناسبت‌های ماه
        evs = []
        for day in range(1, days_in + 1):
            key = f"{month}-{day}"
            for e in shamsi_events.get(key, []):
                if "هیچ مناسبت" not in e:
                    evs.append(f"• {pn(day)}: {e}")
        if evs:
            lines.append("\n📌 مناسبت‌ها:")
            lines.extend(evs[:15])
        return "\n".join(lines)
    except Exception as e:
        return f"❌ خطا: {e}"
