# Auto-split part 6: calculate_age
def calculate_age(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> str:
    """
    محاسبه سن دقیق بر اساس تاریخ تولد شمسی.
    خروجی: سال، ماه، روز، ساعت، دقیقه
    """
    try:
        birth_j = jdatetime.datetime(year, month, day, hour, minute)
        birth_g = birth_j.togregorian()
        birth_aware = tehran_tz.localize(birth_g)

        now = datetime.now(tehran_tz)

        if birth_aware > now:
            return "❌ تاریخ تولد نمی‌تواند در آینده باشد."

        # محاسبه تفاوت دقیق
        delta = now - birth_aware
        total_seconds = int(delta.total_seconds())

        # سال و ماه با جابه‌جایی تقویم شمسی
        now_j = jdatetime.datetime.fromgregorian(datetime=now)
        years = now_j.year - birth_j.year
        months = now_j.month - birth_j.month
        days = now_j.day - birth_j.day

        if days < 0:
            months -= 1
            # تعداد روزهای ماه قبلی
            prev_month = now_j.month - 1 if now_j.month > 1 else 12
            prev_year = now_j.year if now_j.month > 1 else now_j.year - 1
            days_in_prev = jdatetime.date(prev_year, prev_month, 1).daysinmonth
            days += days_in_prev

        if months < 0:
            years -= 1
            months += 12

        # ساعت و دقیقه از باقی‌مانده ثانیه‌ها (تقریبی از زمان دقیق تولد)
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60

        # اگر فقط تاریخ داده شده (ساعت=۰)، ساعت و دقیقه را از نیمه‌شب حساب نکنیم
        # بلکه نشان دهیم «از نیمه‌شب امروز»
        time_part = ""
        if hour != 0 or minute != 0:
            time_part = (
                f"\n🕐 **ساعت:** {to_persian_num(hours)}\n"
                f"⏱ **دقیقه:** {to_persian_num(minutes)}"
            )
        else:
            # سن به روز کامل
            total_days = delta.days
            time_part = f"\n📆 **مجموع روزها:** {to_persian_num(f'{total_days:,}')}"

        birth_str = (
            f"{to_persian_num(day)} {PERSIAN_MONTHS[month]} {to_persian_num(year)}"
        )
        if hour or minute:
            birth_str += f" ساعت {to_persian_num(f'{hour:02d}')}:{to_persian_num(f'{minute:02d}')}"

        return (
            f"🎂 **سن دقیق شما**\n\n"
            f"📅 تاریخ تولد: {birth_str}\n\n"
            f"🗓 **سال:** {to_persian_num(years)}\n"
            f"🗓 **ماه:** {to_persian_num(months)}\n"
            f"🗓 **روز:** {to_persian_num(days)}"
            f"{time_part}"
        )
    except Exception:
        return (
            "❌ تاریخ نامعتبر است.\n"
            "مثال: `1375/03/15`\n"
            "یا با ساعت: `1375/03/15 14:30`"
        )
