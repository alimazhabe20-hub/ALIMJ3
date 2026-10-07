from typing import Optional
from typing import Tuple

# Auto-split part 1: parse_natural_weather
def parse_natural_weather(text: str) -> Optional[Tuple[str, bool]]:
    """تشخیص درخواست طبیعی هوا و تعیین شهر/پیش‌بینی بدون وابستگی به AI."""
    raw = (text or "").strip()
    if not raw:
        return None
    normalized = raw.replace("ي", "ی").replace("ك", "ک").replace("‌", " ")

    # دکمه‌های منوی رسمی باید مسیر معمول خودشان را حفظ کنند.
    if normalized in {"هوا و مکان", "🌤 هوا و مکان", "پیش‌بینی هوا", "🌤 پیش‌بینی هوا", "کیفیت هوا", "🌫 کیفیت هوا"}:
        return None

    if not re.search(r"(?:آب\s*و\s*هوا|هوا|دما|باران|بارون|رگبار|آفتابی|ابری|رطوبت|پیش\s*بینی)", normalized, re.I):
        return None

    # «فردا/پس‌فردا/این هفته...» یعنی پیش‌بینی؛ برای سؤال ساده هوا، وضعیت فعلی را می‌گیریم.
    forecast = bool(re.search(
        r"فردا|پس\s*فردا|امروز\s*و\s*فردا|هفته|روزهای\s*آینده|چند\s*روز|پیش\s*بینی",
        normalized, re.I,
    ))

    from bot.features.weather.weather_extra import CITY_COORDS
    city = ""
    # شهرهای شناخته‌شده را از طولانی‌ترین نام به کوتاه‌ترین بررسی کن.
    for candidate in sorted(CITY_COORDS, key=len, reverse=True):
        if candidate in normalized:
            city = candidate
            break

    # برای «هوا چطوره؟» شهر خالی می‌ماند تا ابزار شهر کاربر را انتخاب کند.
    if not city and not forecast and not re.search(r"چط(?:وره|وری)|چگونه|چجوری|وضعیت|دما", normalized, re.I):
        return None
    return city, forecast
