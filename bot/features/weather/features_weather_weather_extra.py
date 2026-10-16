from bot.utils.quote_ui import section as _qs, quote as _q, bold as _b, esc as _e
"""پیش‌بینی هوا ۷ روزه، AQI واقعی، فاصله شهرها — Open-Meteo (بدون کلید، سریع، پایدار)"""
import math
import httpx
from datetime import datetime
from bot.config import config
from bot.logger import logger
from bot.utils.http_resilience import pooled_client
from bot.utils.http_client import pooled_async_client, request_with_retry

_cache = {}
_cache_t = {}

# مختصات کامل شهرهای ایران و عراق + چند شهر مهم
CITY_COORDS = {
    "تهران": (35.6892, 51.3890), "مشهد": (36.2970, 59.6062), "اصفهان": (32.6546, 51.6680),
    "شیراز": (29.5918, 52.5837), "تبریز": (38.0962, 46.2738), "قم": (34.6416, 50.8746),
    "کرج": (35.8400, 50.9391), "اهواز": (31.3183, 48.6706), "کرمانشاه": (34.3142, 47.0650),
    "ارومیه": (37.5527, 45.0761), "رشت": (37.2808, 49.5832), "کرمان": (30.2832, 57.0788),
    "یزد": (31.8974, 54.3569), "همدان": (34.7983, 48.5146), "اردبیل": (38.2498, 48.2933),
    "زاهدان": (29.4963, 60.8629), "بندرعباس": (27.1832, 56.2666), "ساری": (36.5633, 53.0601),
    "قزوین": (36.2688, 50.0041), "خرم‌آباد": (33.4878, 48.3558), "سنندج": (35.3219, 46.9862),
    "بوشهر": (28.9234, 50.8203), "اراک": (34.0917, 49.6892), "زنجان": (36.6736, 48.4787),
    "گرگان": (36.8427, 54.4439), "سمنان": (35.5769, 53.3953), "بجنورد": (37.4750, 57.3333),
    "ایلام": (33.6374, 46.4226), "یاسوج": (30.6682, 51.5880), "بیرجند": (32.8663, 59.2211),
    "ساوه": (35.0213, 50.3566), "نجف": (31.9956, 44.3147), "کربلا": (32.6163, 44.0249),
    "کاظمین": (33.3800, 44.3400), "سامرا": (34.1959, 43.8730), "بغداد": (33.3152, 44.3661),
    "کیش": (26.5570, 53.9800), "قشم": (26.9581, 56.2719), "چابهار": (25.2919, 60.6430),
}

WEATHER_CODES = {
    0: "آفتابی ☀️", 1: "عمدتاً صاف 🌤", 2: "نیمه‌ابری ⛅", 3: "ابری ☁️",
    45: "مه 🌫", 48: "مه یخی 🌫", 51: "باران ریز 🌦", 53: "باران متوسط 🌧",
    55: "باران شدید 🌧", 61: "باران 🌧", 63: "باران متوسط 🌧", 65: "باران شدید ⛈",
    71: "برف ❄️", 73: "برف متوسط ❄️", 75: "برف سنگین ❄️", 80: "رگبار 🌦",
    81: "رگبار متوسط 🌧", 82: "رگبار شدید ⛈", 95: "رعدوبرق ⛈", 96: "تگرگ 🌨",
}

AQI_LABELS = [
    (0, 50, "عالی 🟢", "هوا پاک است. مناسب همه فعالیت‌ها."),
    (51, 100, "قابل قبول 🟡", "حساس‌ها کمی مراقب باشند."),
    (101, 150, "ناسالم برای گروه‌های حساس 🟠", "کودکان، سالمندان و بیماران ریوی فعالیت سنگین نکنند."),
    (151, 200, "ناسالم 🔴", "فعالیت در فضای باز را کاهش دهید."),
    (201, 300, "بسیار ناسالم 🟣", "از خروج غیرضروری خودداری کنید."),
    (301, 999, "خطرناک ⚫", "فقط در شرایط اضطراری بیرون بروید."),
]

# ===== merged from bot/features/weather/weather_extra_parts/features_weather_weather_extra_parts_part_001_pn.py =====
# Auto-split part 1: pn
def pn(n):
    return str(n).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))

# ===== end merged part =====

# ===== merged from bot/features/weather/weather_extra_parts/part_002__norm_city.py =====
# Auto-split part 2: _norm_city
def _norm_city(city: str) -> str:
    c = (city or "").strip().replace("ي", "ی").replace("ك", "ک")
    return c

# ===== end merged part =====

# ===== merged from bot/features/weather/weather_extra_parts/part_003__get_coords.py =====
# Auto-split part 3: _get_coords
def _get_coords(city: str):
    c = _norm_city(city)
    if c in CITY_COORDS:
        return CITY_COORDS[c]
    # جستجوی جزئی
    for k, v in CITY_COORDS.items():
        if c in k or k in c:
            return v
    return None

# ===== end merged part =====

# ===== merged from bot/features/weather/weather_extra_parts/part_004_weather_forecast.py =====
# Auto-split part 4: weather_forecast
async def weather_forecast(city: str, days: int = 7, start_day: int = 0) -> str:
    """پیش‌بینی هوشمند: حس واقعی، احتمال باران، UV، توصیه لباس/فعالیت."""
    city = _norm_city(city) or "تهران"
    days = max(1, min(int(days or 7), 7))
    start_day = max(0, min(int(start_day or 0), 6))
    key = f"fc7_smart_{city}_{days}_{start_day}"
    now_ts = datetime.now().timestamp()
    if key in _cache and now_ts - _cache_t.get(key, 0) < getattr(config, "CACHE_TTL", 300):
        return _cache[key]

    coords = _get_coords(city)
    if not coords:
        try:
            async with pooled_async_client() as client:
                r = await request_with_retry(
                    "GET",
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

    weekday_fa = {
        0: "دوشنبه", 1: "سه‌شنبه", 2: "چهارشنبه", 3: "پنج‌شنبه",
        4: "جمعه", 5: "شنبه", 6: "یکشنبه",
    }

    def _code_desc(code: int) -> str:
        return WEATHER_CODES.get(int(code or 0), "نامشخص")

    def _uv_label(u) -> str:
        try:
            v = float(u)
        except (TypeError, ValueError):
            return ""
        if v < 3:
            return "کم"
        if v < 6:
            return "متوسط"
        if v < 8:
            return "زیاد — ضدآفتاب"
        return "خیلی زیاد — ضدآفتاب و سایه"

    def _smart_tips(cur_temp, tmax_today, tmin_today, precip_prob, precip_sum, uv, wind, code) -> list[str]:
        tips = []
        try:
            t = float(cur_temp)
        except (TypeError, ValueError):
            t = None
        try:
            mx = float(tmax_today) if tmax_today is not None else None
        except (TypeError, ValueError):
            mx = None
        try:
            mn = float(tmin_today) if tmin_today is not None else None
        except (TypeError, ValueError):
            mn = None
        try:
            pp = float(precip_prob or 0)
        except (TypeError, ValueError):
            pp = 0
        try:
            ps = float(precip_sum or 0)
        except (TypeError, ValueError):
            ps = 0
        try:
            u = float(uv or 0)
        except (TypeError, ValueError):
            u = 0
        try:
            w = float(wind or 0)
        except (TypeError, ValueError):
            w = 0
        code = int(code or 0)

        if t is not None:
            if t <= 5:
                tips.append("🧥 هوا سرد است؛ لباس گرم بپوش.")
            elif t <= 15:
                tips.append("🧣 خنک است؛ یک لایه اضافه همراه داشته باش.")
            elif t >= 33:
                tips.append("🥵 گرم است؛ آب زیاد بنوش و در سایه بمان.")
            elif t >= 28:
                tips.append("☀️ نسبتاً گرم؛ لباس سبک مناسب است.")

        if pp >= 60 or ps >= 3 or code in (61, 63, 65, 80, 81, 82, 95, 96):
            tips.append("☂️ احتمال باران/رگبار — چتر یا بارانی بردار.")
        elif pp >= 30 or ps >= 0.5:
            tips.append("🌦 احتمال بارش کم؛ یک بارانی سبک کافی است.")

        if u >= 6:
            tips.append("🧴 UV بالاست؛ ضدآفتاب و کلاه توصیه می‌شود.")
        if w >= 40:
            tips.append("💨 باد شدید؛ در فضای باز احتیاط کن.")
        elif w >= 25:
            tips.append("🍃 باد نسبتاً تند است.")

        if mx is not None and mn is not None and (mx - mn) >= 14:
            tips.append("🌡 اختلاف شب و روز زیاد است؛ لباس لایه‌لایه بپوش.")

        if not tips:
            tips.append("✅ شرایط مناسب فعالیت روزانه است.")
        return tips[:4]

    data = None
    param_sets = [
        {
            "latitude": lat,
            "longitude": lon,
            "daily": (
                "weather_code,temperature_2m_max,temperature_2m_min,"
                "apparent_temperature_max,apparent_temperature_min,"
                "precipitation_sum,precipitation_probability_max,"
                "windspeed_10m_max,uv_index_max,sunrise,sunset"
            ),
            "current": (
                "temperature_2m,relative_humidity_2m,apparent_temperature,"
                "weather_code,wind_speed_10m,precipitation"
            ),
            "timezone": "Asia/Tehran",
            "forecast_days": 7,
        },
        {
            "latitude": lat,
            "longitude": lon,
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max,uv_index_max",
            "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
            "timezone": "Asia/Tehran",
            "forecast_days": 7,
        },
        {
            "latitude": lat,
            "longitude": lon,
            "daily": "weathercode,temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max,uv_index_max",
            "current_weather": "true",
            "timezone": "Asia/Tehran",
            "forecast_days": 7,
        },
    ]
    for params in param_sets:
        try:
            async with pooled_async_client() as client:
                r = await request_with_retry("GET", "https://api.open-meteo.com/v1/forecast", params=params)
                if r is not None and getattr(r, "status_code", 0) == 200:
                    data = r.json()
                    if data:
                        break
        except Exception as e:
            logger.error(f"open-meteo httpx: {e}")
        try:
            import requests as _req
            r = _req.get(
                "https://api.open-meteo.com/v1/forecast",
                params=params,
                timeout=15,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            if r.status_code == 200:
                data = r.json()
                if data:
                    break
        except Exception as e:
            logger.error(f"open-meteo requests: {e}")

    if data:
        current = data.get("current") or {}
        cw = data.get("current_weather") or {}
        daily = data.get("daily") or {}
        times = daily.get("time") or []
        tmax = daily.get("temperature_2m_max") or []
        tmin = daily.get("temperature_2m_min") or []
        atmax = daily.get("apparent_temperature_max") or []
        atmin = daily.get("apparent_temperature_min") or []
        codes = daily.get("weather_code") or daily.get("weathercode") or []
        precip = daily.get("precipitation_sum") or []
        pprob = daily.get("precipitation_probability_max") or []
        wind = daily.get("windspeed_10m_max") or daily.get("wind_speed_10m_max") or []
        uv = daily.get("uv_index_max") or []
        sunrise = daily.get("sunrise") or []
        sunset = daily.get("sunset") or []

        if current:
            cur_temp = current.get("temperature_2m", "?")
            cur_hum = current.get("relative_humidity_2m", "?")
            cur_app = current.get("apparent_temperature")
            cur_code = current.get("weather_code") or current.get("weathercode") or 0
            cur_wind = current.get("wind_speed_10m", "?")
            cur_precip = current.get("precipitation")
        else:
            cur_temp = cw.get("temperature", "?")
            cur_hum = "?"
            cur_app = None
            cur_code = cw.get("weathercode") or cw.get("weather_code") or 0
            cur_wind = cw.get("windspeed", cw.get("wind_speed", "?"))
            cur_precip = None
        try:
            cur_code = int(cur_code)
        except Exception:
            cur_code = 0
        cur_desc = _code_desc(cur_code)

        # خلاصه هوشمند امروز
        t0_max = tmax[0] if tmax else None
        t0_min = tmin[0] if tmin else None
        p0 = precip[0] if precip else 0
        pp0 = pprob[0] if pprob else 0
        u0 = uv[0] if uv else 0
        w0 = wind[0] if wind else cur_wind
        c0 = codes[0] if codes else cur_code
        tips = _smart_tips(cur_temp, t0_max, t0_min, pp0, p0, u0, w0, c0)

        lines = [
            f"🌤 **پیش‌بینی هوای {city}**",
            f"📅 بازه: {days} روز" + (f" (از روز {start_day + 1})" if start_day else ""),
            "",
            f"📍 **الان:** {pn(cur_temp)}°C  ·  {cur_desc}",
        ]
        if cur_app is not None and cur_app != cur_temp:
            lines.append(f"🌡️ حس واقعی: {pn(cur_app)}°C")
        hum_wind = f"💧 رطوبت: {pn(cur_hum)}%"
        if cur_wind not in (None, "?", ""):
            hum_wind += f"  |  💨 باد: {pn(cur_wind)} km/h"
        lines.append(hum_wind)
        if cur_precip not in (None, 0, 0.0, "0", "0.0"):
            lines.append(f"🌧 بارش لحظه‌ای: {pn(cur_precip)} mm")

        # طلوع/غروب امروز
        if sunrise and sunset:
            try:
                sr = str(sunrise[0]).split("T")[-1][:5]
                ss = str(sunset[0]).split("T")[-1][:5]
                lines.append(f"🌅 طلوع {pn(sr)}  ·  🌇 غروب {pn(ss)}")
            except Exception:
                pass

        lines.append("")
        lines.append("💡 **توصیه هوشمند**")
        for tip in tips:
            lines.append(f"• {tip}")

        lines.append("━━━━━━━━━━━━━━━━━━━━")

        day_names = ["امروز", "فردا", "پس‌فردا", "روز ۴", "روز ۵", "روز ۶", "روز ۷"]
        end_day = min(start_day + days, len(times), 7)
        for i in range(start_day, end_day):
            date_s = times[i] if i < len(times) else ""
            d_short = date_s[5:] if date_s else ""
            wd = ""
            try:
                dt = datetime.strptime(date_s[:10], "%Y-%m-%d")
                wd = weekday_fa.get(dt.weekday(), "")
            except Exception:
                pass
            label = day_names[i] if i < len(day_names) else f"روز {i+1}"
            if wd:
                label = f"{label} · {wd}"

            mx = tmax[i] if i < len(tmax) else "?"
            mn = tmin[i] if i < len(tmin) else "?"
            try:
                code = int(codes[i]) if i < len(codes) else 0
            except Exception:
                code = 0
            desc = _code_desc(code)
            pr = precip[i] if i < len(precip) else 0
            pp = pprob[i] if i < len(pprob) else None
            wd_spd = wind[i] if i < len(wind) else "?"
            u = uv[i] if i < len(uv) else "?"
            amx = atmax[i] if i < len(atmax) else None
            amn = atmin[i] if i < len(atmin) else None

            lines.append(f"**{label}** ({d_short})")
            lines.append(f"  🌡 {pn(mn)}° ~ {pn(mx)}°  ·  {desc}")
            extra = []
            if amx is not None and amn is not None:
                extra.append(f"حس {pn(amn)}°~{pn(amx)}°")
            if pp is not None:
                try:
                    if float(pp) > 0:
                        extra.append(f"احتمال باران {pn(int(float(pp)))}%")
                except (TypeError, ValueError):
                    pass
            if pr not in (None, 0, 0.0, "0", "0.0") and str(pr) not in ("0", "0.0"):
                extra.append(f"بارش {pn(pr)}mm")
            if u not in (None, "?", ""):
                ul = _uv_label(u)
                extra.append(f"UV {pn(u)}" + (f" ({ul})" if ul else ""))
            if wd_spd not in (None, "?", ""):
                extra.append(f"باد {pn(wd_spd)} km/h")
            if extra:
                lines.append("  " + " · ".join(extra))
            lines.append("")

        # جمع‌بندی هفته
        try:
            maxs = [float(x) for x in tmax[:7] if x is not None]
            mins = [float(x) for x in tmin[:7] if x is not None]
            rains = [float(x or 0) for x in precip[:7]]
            if maxs and mins:
                lines.append("📊 **خلاصه هفته**")
                lines.append(
                    f"گرم‌ترین: {pn(f'{max(maxs):.0f}')}°  ·  "
                    f"سردترین: {pn(f'{min(mins):.0f}')}°"
                )
                total_rain = sum(rains)
                if total_rain > 0:
                    lines.append(f"مجموع بارش پیش‌بینی‌شده: {pn(f'{total_rain:.1f}')} mm")
                else:
                    lines.append("بارش قابل‌توجهی در این بازه پیش‌بینی نشده.")
        except Exception:
            pass

        result = "\n".join(lines).rstrip()
        _cache[key] = result
        _cache_t[key] = now_ts
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
                
        _lines = [x for x in result.split(chr(10)) if x is not None]
        _title = _lines[0] if _lines else '🌤'
        _body = chr(10).join(_lines[1:]).strip() if len(_lines) > 1 else result
        return _qs(_title.replace('**','').strip(), _body or result)

    except Exception as e:
        logger.error(f"wttr fallback {city}: {e}")

    return (
        f"❌ پیش‌بینی هوای {city} موقتاً در دسترس نیست.\n"
        "لطفاً چند لحظه بعد دوباره امتحان کنید."
    )

# ===== end merged part =====


# ===== smart air_quality =====
# آستانه‌های WHO برای PM2.5 (µg/m³) — راهنمای سلامت
_PM25_HEALTH = [
    (0, 12, "🟢", "برای همه مناسب است؛ ورزش بیرون بلامانع."),
    (12.1, 35.4, "🟡", "افراد حساس (آسم، قلب) فعالیت سنگین را کم کنند."),
    (35.5, 55.4, "🟠", "کودکان و سالمندان در فضای باز محدود شوند؛ ماسک FFP2 مفید است."),
    (55.5, 150.4, "🔴", "از خروج غیرضروری بپرهیزید؛ ماسک توصیه می‌شود."),
    (150.5, 9999, "⚫", "فقط در اضطرار بیرون بروید؛ پنجره‌ها را ببندید."),
]


def _pm25_advice(pm25) -> tuple[str, str]:
    if pm25 is None:
        return "⚪", "داده PM2.5 در دسترس نیست."
    try:
        v = float(pm25)
    except (TypeError, ValueError):
        return "⚪", "داده PM2.5 نامعتبر."
    for lo, hi, emoji, tip in _PM25_HEALTH:
        if lo <= v <= hi:
            return emoji, tip
    return "⚪", ""


def _trend_arrow(current, previous) -> str:
    if current is None or previous is None:
        return ""
    try:
        d = float(current) - float(previous)
    except (TypeError, ValueError):
        return ""
    if d <= -5:
        return "📉 رو به بهبود"
    if d >= 5:
        return "📈 رو به بدتر شدن"
    return "➡️ تقریباً ثابت"


async def _aqi_for_coords(lat: float, lon: float) -> dict | None:
    """دریافت AQI فعلی + چند ساعت اخیر."""
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": (
            "european_aqi,us_aqi,pm10,pm2_5,carbon_monoxide,"
            "nitrogen_dioxide,ozone,sulphur_dioxide,dust"
        ),
        "hourly": "european_aqi,pm2_5",
        "past_days": 1,
        "forecast_days": 1,
        "timezone": "Asia/Tehran",
    }
    try:
        async with pooled_async_client() as client:
            r = await request_with_retry("GET", url, params=params)
            r.raise_for_status()
            return r.json()
    except Exception as e:
        logger.debug("aqi fetch: %s", e)
        return None


def _hourly_prev(data: dict, key: str, hours_ago: int = 3):
    """مقدار hourly حدود hours_ago ساعت قبل."""
    hourly = (data or {}).get("hourly") or {}
    times = hourly.get("time") or []
    values = hourly.get(key) or []
    if not times or not values:
        return None
    # آخرین مقدار معتبر غیر None را پیدا کن، بعد hours_ago عقب برو
    last_i = None
    for i in range(len(values) - 1, -1, -1):
        if values[i] is not None:
            last_i = i
            break
    if last_i is None:
        return None
    j = last_i - hours_ago
    if j < 0:
        return None
    return values[j]



async def air_quality(city: str) -> str:
    """کیفیت هوای هوشمند: AQI اروپا/آمریکا، روند، هشدار PM2.5، بدون پیشنهاد شهر."""
    key = f"aqi_smart_{city}"
    now = datetime.now().timestamp()
    ttl = getattr(config, "CACHE_TTL", 300)
    if key in _cache and now - _cache_t.get(key, 0) < ttl:
        return _cache[key]

    lat, lon = _get_coords(city)
    try:
        data = await _aqi_for_coords(lat, lon)
        if not data:
            return f"❌ کیفیت هوای {city} موقتاً در دسترس نیست."

        cur = data.get("current") or {}
        aqi = cur.get("european_aqi")
        us_aqi = cur.get("us_aqi")
        pm25 = cur.get("pm2_5")
        pm10 = cur.get("pm10")
        no2 = cur.get("nitrogen_dioxide")
        o3 = cur.get("ozone")
        so2 = cur.get("sulphur_dioxide")
        co = cur.get("carbon_monoxide")
        dust = cur.get("dust")

        label, advice = "نامشخص", ""
        if aqi is not None:
            for low, high, lab, adv in AQI_LABELS:
                if low <= aqi <= high:
                    label, advice = lab, adv
                    break

        # روند نسبت به حدود ۳ ساعت قبل
        prev_aqi = _hourly_prev(data, "european_aqi", 3)
        prev_pm = _hourly_prev(data, "pm2_5", 3)
        trend = _trend_arrow(aqi, prev_aqi)
        pm_trend = _trend_arrow(pm25, prev_pm)

        pm_emoji, pm_tip = _pm25_advice(pm25)

        lines = [
            f"🌫 **کیفیت هوا — {city}** (زنده)",
            "",
            f"📊 **AQI اروپا:** {pn(aqi) if aqi is not None else '—'}  →  **{label}**",
        ]
        if us_aqi is not None:
            lines.append(f"🇺🇸 **AQI آمریکا:** {pn(us_aqi)}")
        if trend:
            lines.append(f"⏱ روند (۳س ساعت اخیر): {trend}")
        lines.append("")
        if advice:
            lines.append(f"💡 {advice}")
        lines.append(f"🫁 PM2.5 {pm_emoji}: {pm_tip}")
        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━━━")
        lines.append(
            f"• PM2.5: {pn(pm25) if pm25 is not None else '—'} µg/m³"
            + (f"  ({pm_trend})" if pm_trend else "")
        )
        lines.append(f"• PM10: {pn(pm10) if pm10 is not None else '—'} µg/m³")
        lines.append(f"• NO₂: {pn(no2) if no2 is not None else '—'} µg/m³")
        lines.append(f"• O₃: {pn(o3) if o3 is not None else '—'} µg/m³")
        lines.append(f"• SO₂: {pn(so2) if so2 is not None else '—'} µg/m³")
        lines.append(f"• CO: {pn(co) if co is not None else '—'} µg/m³")
        if dust is not None:
            lines.append(f"• گردوغبار: {pn(dust)} µg/m³")


        result = "\n".join(lines)
        _cache[key] = result
        _cache_t[key] = now
        
        _lines = [x for x in result.split(chr(10)) if x is not None]
        _title = _lines[0] if _lines else '🌤'
        _body = chr(10).join(_lines[1:]).strip() if len(_lines) > 1 else result
        return _qs(_title.replace('**','').strip(), _body or result)

    except Exception as e:
        logger.error(f"aqi {city}: {e}")
        return f"❌ کیفیت هوای {city} موقتاً در دسترس نیست."


# ===== end merged part =====


# ===== merged from bot/features/weather/weather_extra_parts/part_006_city_distance.py =====
# Auto-split part 6: city_distance
def city_distance(city1: str, city2: str) -> str:
    """فاصله دقیق بین دو شهر با فرمول Haversine"""
    c1 = CITY_COORDS.get(city1.strip())
    c2 = CITY_COORDS.get(city2.strip())
    if not c1 or not c2:
        available = "، ".join(list(CITY_COORDS.keys())[:15]) + " و ..."
        return (
            f"❌ یکی از شهرها پیدا نشد.\n\n"
            f"شهرهای پشتیبانی‌شده:\n{available}\n\n"
            f"مثال: `تهران مشهد`"
        )
    R = 6371.0
    lat1, lon1 = math.radians(c1[0]), math.radians(c1[1])
    lat2, lon2 = math.radians(c2[0]), math.radians(c2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    dist = 2 * R * math.asin(math.sqrt(a))
    hours = dist / 80
    h = int(hours)
    m = int((hours - h) * 60)
    return (
        f"🗺 **فاصله بین شهرها**\n\n"
        f"📍 {city1}  ↔  {city2}\n\n"
        f"📏 فاصله هوایی: **{pn(f'{dist:.0f}')} کیلومتر**\n"
        f"🚗 تقریبی با خودرو: حدود **{pn(h)} ساعت و {pn(m)} دقیقه**"
    )

# ===== end merged part =====
