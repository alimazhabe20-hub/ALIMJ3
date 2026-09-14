# Auto-split part 12: date_diff
def date_diff(y1, m1, d1, y2, m2, d2) -> str:
    try:
        a = jdatetime.date(y1, m1, d1)
        b = jdatetime.date(y2, m2, d2)
        swapped = False
        if a > b:
            a, b = b, a
            y1, m1, d1, y2, m2, d2 = y2, m2, d2, y1, m1, d1
            swapped = True

        total = (b - a).days
        years, months, days = _ymd_diff(a, b)
        total_months = years * 12 + months
        weeks = total // 7
        rem_days = total % 7
        hours = total * 24
        minutes = hours * 60

        ga = a.togregorian()
        gb = b.togregorian()
        ha = _g2h_safe(ga)
        hb = _g2h_safe(gb)

        wd_a = PERSIAN_WEEKDAYS[a.weekday()]
        wd_b = PERSIAN_WEEKDAYS[b.weekday()]

        # روزهای کاری تقریبی (۵/۷)
        workdays = int(total * 5 / 7)

        # مناسبت‌های بین دو تاریخ (نمونه محدود)
        event_count = 0
        try:
            cur = a
            while cur <= b and event_count < 50:
                key = f"{cur.month}-{cur.day}"
                evs = shamsi_events.get(key, [])
                for e in evs:
                    if "هیچ مناسبت" not in e:
                        event_count += 1
                cur = cur + timedelta(days=1)
        except Exception:
            event_count = 0

        direction = ""
        if swapped:
            direction = "⚠️ ترتیب ورودی برعکس بود؛ از تاریخ کوچک‌تر به بزرگ‌تر محاسبه شد.\n\n"

        lines = [
            "📅 **اختلاف دو تاریخ (پیشرفته)**\n",
            direction,
            f"🔹 از: {wd_a} {pn(d1)} {PERSIAN_MONTHS[m1]} {pn(y1)}",
            f"   📆 میلادی: {ga.day} {GREGORIAN_MONTHS[ga.month]} {ga.year}",
            f"   🌙 قمری: {pn(ha[2])} {ha[3]} {pn(ha[0])}" if ha[0] else "   🌙 قمری: —",
            "",
            f"🔸 تا: {wd_b} {pn(d2)} {PERSIAN_MONTHS[m2]} {pn(y2)}",
            f"   📆 میلادی: {gb.day} {GREGORIAN_MONTHS[gb.month]} {gb.year}",
            f"   🌙 قمری: {pn(hb[2])} {hb[3]} {pn(hb[0])}" if hb[0] else "   🌙 قمری: —",
            "",
            "━━━━━━━━━━━━━━━━━━━━",
            f"🗓 دقیق: **{pn(years)}** سال و **{pn(months)}** ماه و **{pn(days)}** روز",
            f"📊 مجموع ماه‌ها: {pn(total_months)} ماه",
            f"📆 مجموع روزها: {pn(f'{total:,}')} روز",
            f"🗓 هفته‌ها: {pn(weeks)} هفته و {pn(rem_days)} روز",
            f"🕐 ساعت تقریبی: {pn(f'{hours:,}')} ساعت",
            f"⏱ دقیقه تقریبی: {pn(f'{minutes:,}')} دقیقه",
            f"💼 روز کاری تقریبی: {pn(f'{workdays:,}')} روز",
        ]
        if event_count:
            lines.append(f"📌 مناسبت‌های ثبت‌شده در این بازه: حدود {pn(event_count)}")
        lines.append("")
        lines.append(f"📈 میانگین: حدود {pn(round(total / 365.25, 2))} سال خورشیدی")
        return "\n".join(lines)
    except Exception:
        return "❌ فرمت: `1375/03/15 1403/05/18`"
