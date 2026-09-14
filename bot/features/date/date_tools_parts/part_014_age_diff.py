# Auto-split part 14: age_diff
def age_diff(y1, m1, d1, y2, m2, d2) -> str:
    try:
        today = jdatetime.datetime.now().date()
        a = jdatetime.date(y1, m1, d1)  # نفر اول
        b = jdatetime.date(y2, m2, d2)  # نفر دوم

        # سن هر نفر تا امروز
        def age_until(birth, until):
            if birth > until:
                return None
            return _ymd_diff(birth, until)

        age_a = age_until(a, today)
        age_b = age_until(b, today)
        if age_a is None or age_b is None:
            return "❌ تاریخ تولد نمی‌تواند در آینده باشد."

        # اختلاف تولدها
        older, younger = (a, b) if a <= b else (b, a)
        older_label = "نفر اول" if a <= b else "نفر دوم"
        younger_label = "نفر دوم" if a <= b else "نفر اول"
        dy, dm, dd = _ymd_diff(older, younger)
        total_days = (younger - older).days

        # سن قمری تقریبی
        def lunar_years(birth):
            days_alive = (today - birth).days
            return round(days_alive / 354.367, 1)

        # درصد عمر (فرض ۷۵ سال)
        def life_pct(birth):
            days_alive = (today - birth).days
            return min(100, round(days_alive / (75 * 365.25) * 100, 1))

        ga = a.togregorian()
        gb = b.togregorian()

        lines = [
            "👥 **اختلاف سن دو نفر (پیشرفته)**\n",
            f"👤 نفر اول: {pn(d1)} {PERSIAN_MONTHS[m1]} {pn(y1)}",
            f"   سن فعلی: {pn(age_a[0])} سال و {pn(age_a[1])} ماه و {pn(age_a[2])} روز",
            f"   سن قمری ≈ {pn(lunar_years(a))} سال | عمر ≈ {pn(life_pct(a))}٪",
            f"   میلادی: {ga.day} {GREGORIAN_MONTHS[ga.month]} {ga.year}",
            "",
            f"👤 نفر دوم: {pn(d2)} {PERSIAN_MONTHS[m2]} {pn(y2)}",
            f"   سن فعلی: {pn(age_b[0])} سال و {pn(age_b[1])} ماه و {pn(age_b[2])} روز",
            f"   سن قمری ≈ {pn(lunar_years(b))} سال | عمر ≈ {pn(life_pct(b))}٪",
            f"   میلادی: {gb.day} {GREGORIAN_MONTHS[gb.month]} {gb.year}",
            "",
            "━━━━━━━━━━━━━━━━━━━━",
            f"🏆 بزرگ‌تر: **{older_label}**",
            f"📏 اختلاف سن: **{pn(dy)}** سال و **{pn(dm)}** ماه و **{pn(dd)}** روز",
            f"📆 اختلاف تولد: {pn(f'{total_days:,}')} روز ≈ {pn(total_days // 7)} هفته",
            f"📊 اختلاف به ماه: {pn(dy * 12 + dm)} ماه",
        ]

        # کی اختلاف به عدد رند می‌رسد؟
        # مثلاً وقتی اختلاف دقیقاً N سال کامل شود (از الان به بعد معنا ندارد چون ثابت است)
        # به‌جای آن: چند سال دیگر نفر کوچک‌تر به سن فعلی نفر بزرگ‌تر می‌رسد
        if a != b:
            older_age_y = age_a[0] if a <= b else age_b[0]
            younger_birth = younger
            # تاریخ رسیدن کوچک‌تر به سن فعلی بزرگ‌تر
            target_y = younger_birth.year + older_age_y
            try:
                target = jdatetime.date(target_y, younger_birth.month, younger_birth.day)
                if target < today:
                    target = jdatetime.date(target_y + 1, younger_birth.month, younger_birth.day)
                left = (target - today).days
                if left >= 0:
                    lines.append(
                        f"\n🎯 {younger_label} حدود {pn(left)} روز دیگر "
                        f"به سن فعلی {older_label} می‌رسد "
                        f"({pn(target.day)} {PERSIAN_MONTHS[target.month]} {pn(target.year)})"
                    )
            except Exception:
                pass

        # نسبت سنی
        days_a = (today - a).days
        days_b = (today - b).days
        if min(days_a, days_b) > 0:
            ratio = max(days_a, days_b) / min(days_a, days_b)
            lines.append(f"📐 نسبت سنی: {pn(round(ratio, 2))} برابر")

        return "\n".join(lines)
    except Exception:
        return "❌ فرمت: `1375/03/15 1380/06/20`"
