# Auto-split part 5: get_next_prayer_time
def get_next_prayer_time(prayer_times, now_dt):
    """محاسبه زمان باقی‌مانده تا اذان بعدی با کلیدهای فارسی"""
    if not prayer_times:
        return None, None

    prayer_keys = ["اذان صبح", "اذان ظهر", "اذان عصر", "اذان مغرب", "اذان عشاء"]
    today = now_dt.date()
    prayer_datetimes = []

    for key in prayer_keys:
        if key in prayer_times:
            try:
                hour, minute = map(int, prayer_times[key].split(":")[:2])
                dt = datetime.combine(
                    today, datetime.min.time().replace(hour=hour, minute=minute)
                )
                dt = tehran_tz.localize(dt)
                prayer_datetimes.append((key, dt))
            except Exception:
                continue

    if not prayer_datetimes:
        return None, None

    future_prayers = [(key, dt) for key, dt in prayer_datetimes if dt > now_dt]
    if future_prayers:
        next_prayer = min(future_prayers, key=lambda x: x[1])
        return next_prayer[0], next_prayer[1] - now_dt
    else:
        next_day_prayers = [
            (key, dt + timedelta(days=1)) for key, dt in prayer_datetimes
        ]
        next_prayer = min(next_day_prayers, key=lambda x: x[1])
        return next_prayer[0], next_prayer[1] - now_dt
