# Auto-split part 17: search_events
def search_events(query: str) -> str:
    q = query.strip()
    if len(q) < 2:
        return "❌ حداقل ۲ حرف بنویسید."
    today = jdatetime.datetime.now().date()
    results = []

    # شمسی با روز مانده
    for key, evs in shamsi_events.items():
        try:
            m, d = map(int, key.split("-"))
        except Exception:
            continue
        for e in evs:
            if q not in e or "هیچ مناسبت" in e:
                continue
            # امسال یا سال بعد
            try:
                target = jdatetime.date(today.year, m, d)
            except Exception:
                continue
            if target < today:
                try:
                    target = jdatetime.date(today.year + 1, m, d)
                except Exception:
                    continue
            days = (target - today).days
            when = "امروز" if days == 0 else f"{pn(days)} روز مانده"
            results.append((days, f"• {e}\n  📅 {pn(d)} {PERSIAN_MONTHS[m]} — {when}"))

    # قمری با روز مانده
    try:
        g = today.togregorian()
        h = Gregorian(g.year, g.month, g.day).to_hijri()
    except Exception:
        h = None
    if h:
        for key, evs in hijri_events.items():
            try:
                m, d = map(int, key.split("-"))
            except Exception:
                continue
            for e in evs:
                if q not in e:
                    continue
                for yoff in (0, 1):
                    try:
                        th = Hijri(h.year + yoff, m, d)
                        if th < h:
                            continue
                        tg = th.to_gregorian()
                        tj = jdatetime.date.fromgregorian(date=tg)
                        days = (tj - today).days
                        if days < 0:
                            continue
                        when = "امروز" if days == 0 else f"{pn(days)} روز مانده"
                        results.append((days, f"• {e}\n  🌙 {pn(d)} {HIJRI_MONTHS.get(m, m)} قمری — {when}"))
                        break
                    except Exception:
                        continue

    if not results:
        return f"❌ مناسبتی با «{q}» پیدا نشد."
    results.sort(key=lambda x: x[0])
    lines = [f"🔍 مناسبت‌یاب: «{q}»\n"]
    for _, line in results[:20]:
        lines.append(line)
    return "\n".join(lines)
