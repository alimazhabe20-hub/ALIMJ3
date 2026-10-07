"""ai_tools: basic responsibilities."""
from .ai_tools_common import *  # noqa: F401,F403
from . import ai_tools_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


async def _get_weather(city: str = "", user_id: int = 0) -> str:
    from bot.api.api_weather import get_weather
    from bot.database import get_user_city

    city = (city or "").strip() or (get_user_city(user_id) or "تهران")
    data = await asyncio.to_thread(get_weather, city)
    if not data:
        return f"آب‌وهوای «{city}» پیدا نشد."
    return (
        f"آب‌وهوای {city}:\n"
        f"دما: {data.get('temp')}°C\n"
        f"وضعیت: {data.get('condition')}\n"
        f"رطوبت: {data.get('humidity')}%"
    )

async def _get_weather_forecast(city: str = "", days: int = 7, start_day: int = 0, user_id: int = 0) -> str:
    from bot.features.weather.features_weather_weather_extra import weather_forecast
    from bot.database import get_user_city

    city = (city or "").strip() or (get_user_city(user_id) or "تهران")
    return await weather_forecast(city, days=int(days or 7), start_day=int(start_day or 0))

async def _get_air_quality(city: str = "", user_id: int = 0) -> str:
    from bot.features.weather.features_weather_weather_extra import air_quality
    from bot.database import get_user_city

    city = (city or "").strip() or (get_user_city(user_id) or "تهران")
    return await air_quality(city)

async def _get_prayer_times(
    city: str = "", country: str = "Iran", user_id: int = 0
) -> str:
    from bot.api.prayer import get_prayer_times
    from bot.database import get_user_city

    city = (city or "").strip() or (get_user_city(user_id) or "قم")
    data = get_prayer_times(city, country or "Iran")
    if not data:
        return f"اوقات شرعی «{city}» پیدا نشد."
    lines = [f"اوقات شرعی {city}:"]
    for k, v in data.items():
        lines.append(f"{k}: {v}")
    return "\n".join(lines)

async def _convert_currency(amount: float, from_cur: str, to_cur: str = "") -> str:
    from bot.features.market.finance import convert_currency

    return await convert_currency(float(amount), str(from_cur), str(to_cur or ""))

async def _convert_crypto(amount: float, symbol: str) -> str:
    from bot.features.market.finance import convert_crypto

    return await convert_crypto(float(amount), str(symbol))

def _calculator(expression: str) -> str:
    from bot.features.tools.features_tools_app_tools import calculator

    return calculator(expression)

def _generate_password(length: int = 16) -> str:
    from bot.features.tools.features_tools_app_tools import generate_password

    return generate_password(int(length or 16))

def _count_text(text: str) -> str:
    from bot.features.tools.features_tools_app_tools import count_text

    return count_text(text)

async def _world_distance(place1: str, place2: str = "") -> str:
    from bot.features.tools.features_tools_app_tools import world_distance

    return await world_distance(place1, place2 or None)

def _convert_date(date_text: str) -> str:
    from bot.features.date.features_date_date_tools import parse_any_date, convert_with_weekday

    p = parse_any_date(date_text)
    if not p:
        return "تاریخ نامعتبر. مثال: 1403/05/18 یا 2024/08/09"
    return convert_with_weekday(p[0], p[1], p[2], p[3])

def _calculate_age(birth_date: str) -> str:
    from bot.features.date.features_date_date_tools import parse_shamsi
    from bot.features.date.features_date_converters import calculate_age

    p = parse_shamsi(birth_date)
    if not p:
        return "تاریخ تولد نامعتبر. مثال: 1375/03/15"
    return calculate_age(p[0], p[1], p[2])

def _birthday_countdown(birth_date: str) -> str:
    from bot.features.date.features_date_date_tools import parse_shamsi, birthday_countdown

    p = parse_shamsi(birth_date)
    if not p:
        return "تاریخ نامعتبر. مثال: 1375/03/15"
    return birthday_countdown(p[0], p[1], p[2])

def _zodiac_animal(birth_date: str) -> str:
    from bot.features.date.features_date_date_tools import parse_shamsi, zodiac_animal

    p = parse_shamsi(birth_date)
    if not p:
        return "تاریخ نامعتبر."
    return zodiac_animal(p[0], p[1], p[2])

def _lunar_age(birth_date: str) -> str:
    from bot.features.date.features_date_date_tools import parse_shamsi, lunar_age

    p = parse_shamsi(birth_date)
    if not p:
        return "تاریخ نامعتبر."
    return lunar_age(p[0], p[1], p[2])

def _current_datetime(timezone_name: str = "", relative_day: int = 0) -> str:
    from bot.services.current_datetime import current_datetime

    return current_datetime(timezone_name, relative_day=relative_day)

def _world_clock() -> str:
    from bot.features.date.features_date_date_tools import world_clock

    return world_clock()

def _month_calendar() -> str:
    from bot.features.date.features_date_date_tools import month_calendar

    return month_calendar()

def _nowruz_countdown() -> str:
    from bot.features.date.features_date_date_tools import nowruz_countdown

    return nowruz_countdown()

def _search_events(query: str) -> str:
    from bot.features.date.features_date_date_tools import search_events

    return search_events(query)

def _qibla_direction(city: str = "", user_id: int = 0) -> str:
    from bot.features.religious.qibla import qibla_direction
    from bot.database import get_user_city

    city = (city or "").strip() or (get_user_city(user_id) or "تهران")
    return qibla_direction(city)

def _daily_adhkar(user_id: int = 0) -> str:
    from bot.features.religious.adhkar import daily_adhkar

    return daily_adhkar(user_id)

async def _daily_verse_hadith(user_id: int = 0) -> str:
    from bot.features.religious.verse_hadith import daily_verse_hadith

    return await daily_verse_hadith(user_id)

def _religious_countdown() -> str:
    from bot.features.religious.features_religious_events import religious_countdown

    return religious_countdown()

async def _istikhara(user_id: int = 0) -> str:
    from bot.features.religious.istikhara import istikhara

    return await istikhara(user_id)

async def _hafez_fal(user_id: int = 0) -> str:
    from bot.features.fun.features_fun_fun_tools import hafez_fal

    return await hafez_fal(user_id)

async def _joke(category: str = "", user_id: int = 0) -> str:
    from bot.features.fun.features_fun_fun_tools import random_joke

    return random_joke(category or None, user_id)

async def _fact_of_day() -> str:
    from bot.features.fun.features_fun_fun_tools import fact_of_day

    return await fact_of_day()

async def _daily_challenge() -> str:
    from bot.features.fun.features_fun_fun_tools import daily_challenge

    return await daily_challenge()

def _apply_font(text: str, style_key: str = "") -> str:
    from bot.features.fonts.converter import apply_font, apply_all_fonts, list_fonts

    if not text:
        return "متنی برای تبدیل فونت نفرستادی."
    if not style_key:
        return apply_all_fonts(text)
    try:
        return apply_font(text, style_key)
    except Exception:
        return list_fonts() + "\n\n" + apply_all_fonts(text)

def _list_fonts() -> str:
    from bot.features.fonts.converter import list_fonts

    return list_fonts()

def _get_user_city(user_id: int = 0) -> str:
    from bot.database import get_user_city

    city = get_user_city(user_id) if user_id else None
    return f"شهر ثبت‌شده کاربر: {city or 'نامشخص'}"

def _city_distance(city1: str, city2: str) -> str:
    from bot.features.weather.features_weather_weather_extra import city_distance

    return city_distance(city1, city2)

def _profile_summary(user_id: int = 0) -> str:
    from bot.features.profile.profile import profile_text
    from bot.database import get_user

    row = get_user(user_id) if user_id else None
    first_name = row[1] if row else "کاربر"
    return profile_text(user_id, first_name)
