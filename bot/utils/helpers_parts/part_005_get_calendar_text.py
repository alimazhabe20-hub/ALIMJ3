# Auto-split part 5: get_calendar_text
def get_calendar_text(year, month, day, user_id):
    """متن تقویم برای روز انتخاب‌شده — مناسبت + اوقات شرعی همان روز + هوا همان روز"""
    try:
        import httpx
        from bot.features.weather.weather_extra import CITY_COORDS, WEATHER_CODES, _norm_city

        target = jdatetime.date(year, month, day)
        date_str = (
            f"{PERSIAN_WEEKDAYS[target.weekday()]} "
            f"{to_persian_num(target.day)} {PERSIAN_MONTHS[target.month]} "
            f"{to_persian_num(target.year)}"
        )
        shamsi = get_shamsi_events(year, month, day)
        shamsi_text = chr(10).join([f"• {e}" for e in shamsi]) if shamsi else "• هیچ مناسبت خاصی ثبت نشده است."

        hijri = get_hijri_date(target.togregorian())
        hijri_events_list = get_hijri_events(hijri['month'], hijri['day'])
        hijri_text = chr(10).join([f"• {e}" for e in hijri_events_list]) if hijri_events_list else "• هیچ مناسبت قمری خاصی ثبت نشده است."

        city = get_user_city(user_id) or "تهران"
        country = get_user_country(user_id) or "Iran"
        g = target.togregorian()
        # Aladhan: DD-MM-YYYY
        g_str = f"{g.day:02d}-{g.month:02d}-{g.year}"
        prayer = get_prayer_times_for_date(city, g_str, country=country)
        if prayer:
            prayer_text = chr(10).join([f"🕌 {k}: {v}" for k, v in prayer.items()])
        else:
            prayer_text = "⚠️ اوقات شرعی در دسترس نیست."


        # هوا: اول Open-Meteo حرفه‌ای ۷روزه از همان روز، بعد fallback
        weather_text = "⚠️ آب و هوا در دسترس نیست."
        try:
            from bot.features.weather.weather_extra import CITY_COORDS, WEATHER_CODES, _norm_city
            import requests as _req
            cname = _norm_city(city)
            coords = CITY_COORDS.get(cname) or CITY_COORDS.get("تهران")
            lat, lon = coords
            start = f"{g.year:04d}-{g.month:02d}-{g.day:02d}"
            from datetime import timedelta as _td
            end_d = g + _td(days=6)
            end = f"{end_d.year:04d}-{end_d.month:02d}-{end_d.day:02d}"
            params = {
                "latitude": lat,
                "longitude": lon,
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max",
                "timezone": "Asia/Tehran",
                "start_date": start,
                "end_date": end,
            }
            r = _req.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=12)
            if r.status_code == 200:
                daily = r.json().get("daily", {})
                times = daily.get("time") or []
                tmax = daily.get("temperature_2m_max") or []
                tmin = daily.get("temperature_2m_min") or []
                codes = daily.get("weather_code") or daily.get("weathercode") or []
                wind = daily.get("windspeed_10m_max") or []
                precip = daily.get("precipitation_sum") or []
                names = ["روز۱", "روز۲", "روز۳", "روز۴", "روز۵", "روز۶", "روز۷"]
                lines = ["🌤 پیش‌بینی ۷روزه (از این تاریخ)"]
                for i in range(min(7, len(times))):
                    d = times[i][5:] if times[i] else ""
                    mx = tmax[i] if i < len(tmax) else "?"
                    mn = tmin[i] if i < len(tmin) else "?"
                    try:
                        code = int(codes[i]) if i < len(codes) else 0
                    except Exception:
                        code = 0
                    desc = WEATHER_CODES.get(code, "")
                    wd = wind[i] if i < len(wind) else "?"
                    lines.append(f"• {names[i]} ({d}): {to_persian_num(mn)}°~{to_persian_num(mx)}° {desc}")
                weather_text = chr(10).join(lines)
            else:
                weather = get_weather(city)
                if weather:
                    from bot.features.weather.weather import format_weather
                    weather_text = format_weather(city, weather)
        except Exception as e:
            from bot.logger import logger
            logger.error(f"calendar weather: {e}")
            weather = get_weather(city)
            if weather:
                from bot.features.weather.weather import format_weather
                weather_text = format_weather(city, weather)

        return (
            f"📅 {date_str}" + chr(10) +
            f"🌙 قمری: {to_persian_num(hijri['day'])} {hijri['month_name']} {to_persian_num(hijri['year'])}" + chr(10)*2 +
            f"📌 مناسبت‌های شمسی:" + chr(10) + shamsi_text + chr(10)*2 +
            f"📌 مناسبت‌های قمری:" + chr(10) + hijri_text + chr(10)*2 +
            f"⏰ اوقات شرعی ({city}) — همین روز" + chr(10) + prayer_text + chr(10)*2 +
            f"🌦️ آب و هوا (۷ روز از این تاریخ)" + chr(10) + weather_text + chr(10)*2 +
            "🔄 با دکمه‌های زیر روز یا ماه را تغییر دهید."
        )
    except Exception as e:
        from bot.logger import logger
        logger.error(f"get_calendar_text: {e}")
        return "❌ خطا در نمایش تقویم."
