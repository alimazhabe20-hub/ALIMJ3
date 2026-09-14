# Auto-split part 4: weather_forecast
async def weather_forecast(city: str, days: int = 7, start_day: int = 0) -> str:
    """پیش‌بینی هوا با بازه انتخابی؛ پیش‌فرض همان ۷ روز قبلی است."""
    city = _norm_city(city) or "تهران"
    days = max(1, min(int(days or 7), 7))
    start_day = max(0, min(int(start_day or 0), 6))
    key = f"fc7_{city}_{days}_{start_day}"
    now = datetime.now().timestamp()
    if key in _cache and now - _cache_t.get(key, 0) < getattr(config, "CACHE_TTL", 300):
        return _cache[key]

    coords = _get_coords(city)
    if not coords:
        try:
            async with pooled_async_client() as client:
                r = await request_with_retry("GET", 
                    "https://nominatim.openstreetmap.org/search",
                    params={"q": city + ", Iran", "format": "json", "limit": 1},
                )
                if r.status_code == 200 and r.json():
                    item = r.json()[0]
                    coords = (float(item["lat"]), float(item["lon"]))
        except Exception as e:
            logger.error(f"geocode weather {city}: {e}")
    if not coords:
        coords = CITY_COORDS.get("تهران")
    lat, lon = coords

    data = None
    # چند شکل پارامتر + httpx و requests
    param_sets = [
        {
            "latitude": lat, "longitude": lon,
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max,uv_index_max",
            "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
            "timezone": "Asia/Tehran", "forecast_days": 7,
        },
        {
            "latitude": lat, "longitude": lon,
            "daily": "weathercode,temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max,uv_index_max",
            "current_weather": "true",
            "timezone": "Asia/Tehran", "forecast_days": 7,
        },
    ]
    for params in param_sets:
        try:
            async with pooled_async_client() as client:
                r = await request_with_retry("GET", "https://api.open-meteo.com/v1/forecast", params=params)
                if r.status_code == 200:
                    data = r.json()
                    break
        except Exception as e:
            logger.error(f"open-meteo httpx: {e}")
        try:
            import requests as _req
            r = _req.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=15,
                         headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                data = r.json()
                break
        except Exception as e:
            logger.error(f"open-meteo requests: {e}")

    if data:
        # پشتیبانی هر دو فرمت current / current_weather
        current = data.get("current") or {}
        cw = data.get("current_weather") or {}
        daily = data.get("daily") or {}
        times = daily.get("time") or []
        tmax = daily.get("temperature_2m_max") or []
        tmin = daily.get("temperature_2m_min") or []
        codes = daily.get("weather_code") or daily.get("weathercode") or []
        precip = daily.get("precipitation_sum") or []
        wind = daily.get("windspeed_10m_max") or daily.get("wind_speed_10m_max") or []
        uv = daily.get("uv_index_max") or []

        if current:
            cur_temp = current.get("temperature_2m", "?")
            cur_hum = current.get("relative_humidity_2m", "?")
            cur_code = current.get("weather_code") or current.get("weathercode") or 0
            cur_wind = current.get("wind_speed_10m", "?")
        else:
            cur_temp = cw.get("temperature", "?")
            cur_hum = "?"
            cur_code = cw.get("weathercode") or cw.get("weather_code") or 0
            cur_wind = cw.get("windspeed", cw.get("wind_speed", "?"))
        try:
            cur_code = int(cur_code)
        except Exception:
            cur_code = 0
        cur_desc = WEATHER_CODES.get(cur_code, "نامشخص")

        lines = [
            f"🌤 پیش‌بینی هوای {city}" + (" (۷ روزه)" if days == 7 and start_day == 0 else ""),
            "",
            f"📍 الان: {pn(cur_temp)}°C  {cur_desc}",
            f"💧 رطوبت: {pn(cur_hum)}%  |  💨 باد: {pn(cur_wind)} km/h",
            "━━━━━━━━━━━━━━━━━━━━",
        ]
        day_names = ["امروز", "فردا", "پس‌فردا", "روز ۴", "روز ۵", "روز ۶", "روز ۷"]
        end_day = min(start_day + days, len(times), 7)
        for i in range(start_day, end_day):
            d = times[i][5:] if times[i] else ""
            mx = tmax[i] if i < len(tmax) else "?"
            mn = tmin[i] if i < len(tmin) else "?"
            try:
                code = int(codes[i]) if i < len(codes) else 0
            except Exception:
                code = 0
            desc = WEATHER_CODES.get(code, "")
            pr = precip[i] if i < len(precip) else 0
            wd = wind[i] if i < len(wind) else "?"
            u = uv[i] if i < len(uv) else "?"
            rain = f"  |  🌧 {pn(pr)}mm" if pr not in (None, 0, "0", 0.0) and str(pr) not in ("0", "0.0") else ""
            lines.append(f"• {day_names[i]} ({d})")
            lines.append(f"  {pn(mn)}° ~ {pn(mx)}°  {desc}")
            lines.append(f"  💨 {pn(wd)} km/h  |  ☀️ UV {pn(u)}{rain}")

        result = "\n".join(lines)
        _cache[key] = result
        _cache_t[key] = now
        return result

    # ——— fallback wttr (حداکثر ۳ روز دارد) + ترجمه ———
    EN2FA = {
        "Sunny": "آفتابی ☀️", "Clear": "صاف ☀️", "Partly cloudy": "نیمه‌ابری ⛅",
        "Cloudy": "ابری ☁️", "Overcast": "ابری کامل ☁️", "Mist": "مه 🌫",
        "Patchy rain possible": "احتمال باران 🌦", "Rain": "بارانی 🌧",
        "Thundery outbreaks possible": "رعدوبرق ⛈", "Snow": "برفی ❄️",
    }
    try:
        async with pooled_async_client() as client:
            r = await request_with_retry("GET", f"https://wttr.in/{city}?format=j1&lang=fa")
            if r.status_code != 200:
                r = await request_with_retry("GET", f"https://wttr.in/{city}?format=j1")
            if r.status_code == 200:
                j = r.json()
                cur = j["current_condition"][0]
                days = j.get("weather", [])[:7]
                desc0 = cur.get("lang_fa", [{}])
                if isinstance(desc0, list) and desc0:
                    cur_desc = desc0[0].get("value") or cur.get("weatherDesc", [{}])[0].get("value", "")
                else:
                    cur_desc = cur.get("weatherDesc", [{}])[0].get("value", "")
                cur_desc = EN2FA.get(cur_desc, cur_desc)
                lines = [
                    f"🌤 پیش‌بینی هوای {city}" + (" (۷ روزه)" if days == 7 and start_day == 0 else ""),
                    "",
                    f"📍 الان: {pn(cur.get('temp_C','?'))}°C — {cur_desc}",
                    f"💧 رطوبت: {pn(cur.get('humidity','?'))}%",
                    "━━━━━━━━━━━━━━━━━━━━",
                ]
                names = ["امروز", "فردا", "پس‌فردا", "روز ۴", "روز ۵", "روز ۶", "روز ۷"]
                selected_days = days[start_day:start_day + days] if isinstance(days, list) else []
                for i, d in enumerate(selected_days, start_day):
                    mx, mn = d.get("maxtempC", "?"), d.get("mintempC", "?")
                    desc = ""
                    try:
                        if d.get("hourly") and d["hourly"][0].get("lang_fa"):
                            desc = d["hourly"][4 if len(d["hourly"])>4 else 0]["lang_fa"][0]["value"]
                        else:
                            desc = d["hourly"][4 if len(d["hourly"])>4 else 0]["weatherDesc"][0]["value"]
                    except Exception:
                        pass
                    desc = EN2FA.get(desc, desc)
                    lines.append(f"• {names[i]}: {pn(mn)}° ~ {pn(mx)}°  {desc}")
                result = "\n".join(lines)
                _cache[key] = result
                _cache_t[key] = now
                return result
    except Exception as e:
        logger.error(f"wttr fallback {city}: {e}")

    return (
        f"❌ پیش‌بینی هوای {city} موقتاً در دسترس نیست.\n"
        "لطفاً چند لحظه بعد دوباره امتحان کنید."
    )
