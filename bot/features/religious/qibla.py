"""قبله‌نما هوشمند v2

- زاویه قبله از شمال حقیقی (great-circle)
- فاصله تا کعبه
- دستورالعمل قطب‌نما
- هشدار شمال مغناطیسی + تقریب میل مغناطیسی ایران
- پشتیبانی از موقعیت لحظه‌ای (lat/lon) علاوه بر شهر
"""

from __future__ import annotations

import math
from typing import Optional, Tuple

try:
    from bot.features.weather.features_weather_weather_extra import CITY_COORDS
except Exception:  # pragma: no cover
    CITY_COORDS = {
        "تهران": (35.6892, 51.3890),
        "مشهد": (36.2970, 59.6062),
        "اصفهان": (32.6546, 51.6680),
        "شیراز": (29.5918, 52.5837),
        "تبریز": (38.0962, 46.2738),
        "قم": (34.6416, 50.8746),
    }

# مختصات کعبه (درجه)
KAABA_LAT = 21.4225
KAABA_LON = 39.8262
KAABA = (KAABA_LAT, KAABA_LON)

# شعاع میانگین زمین (کیلومتر) برای فاصله
_EARTH_KM = 6371.0

# تقریب میل مغناطیسی (declination) برای چند منطقه ایران — درجه
# مثبت = شرقی (شمال مغناطیسی شرق شمال حقیقی)
# مقادیر تقریبی و پایدار برای کاربرد روزمره؛ برای نقشه‌برداری دقیق از مدل IGRF استفاده شود.
_DECLINATION_BY_CITY = {
    "تهران": 4.5,
    "کرج": 4.5,
    "قم": 4.3,
    "اصفهان": 4.0,
    "شیراز": 3.5,
    "مشهد": 5.0,
    "تبریز": 5.5,
    "اهواز": 3.8,
    "کرمانشاه": 4.8,
    "رشت": 5.2,
    "یزد": 3.8,
    "کرمان": 3.2,
    "زاهدان": 2.8,
    "بندرعباس": 2.5,
    "ساری": 5.0,
    "ارومیه": 5.5,
    "همدان": 4.6,
    "اراک": 4.2,
}
_DEFAULT_DECLINATION_IR = 4.2


def _bearing_true(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """زاویه اولیه مسیر دایره عظیمه از نقطه ۱ به ۲ — درجه ساعت‌گرد از شمال حقیقی."""
    φ1, λ1 = math.radians(lat1), math.radians(lon1)
    φ2, λ2 = math.radians(lat2), math.radians(lon2)
    dλ = λ2 - λ1
    x = math.sin(dλ) * math.cos(φ2)
    y = math.cos(φ1) * math.sin(φ2) - math.sin(φ1) * math.cos(φ2) * math.cos(dλ)
    brng = math.degrees(math.atan2(x, y))
    return (brng + 360.0) % 360.0


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """فاصله تقریبی روی کره زمین (کیلومتر)."""
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    dφ = math.radians(lat2 - lat1)
    dλ = math.radians(lon2 - lon1)
    a = math.sin(dφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(dλ / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return _EARTH_KM * c


def _cardinal_name(bearing: float) -> str:
    """نزدیک‌ترین جهت اصلی/فرعی فارسی."""
    directions = [
        (0, "شمال"),
        (45, "شمال‌شرقی"),
        (90, "شرق"),
        (135, "جنوب‌شرقی"),
        (180, "جنوب"),
        (225, "جنوب‌غربی"),
        (270, "غرب"),
        (315, "شمال‌غربی"),
        (360, "شمال"),
    ]
    return min(directions, key=lambda d: abs(d[0] - bearing))[1]


def _declination_for(city: Optional[str], lat: Optional[float] = None) -> float:
    """میل مغناطیسی تقریبی (درجه، شرقی مثبت)."""
    if city:
        c = str(city).strip()
        if c in _DECLINATION_BY_CITY:
            return _DECLINATION_BY_CITY[c]
        # تطبیق جزئی
        for k, v in _DECLINATION_BY_CITY.items():
            if k in c or c in k:
                return v
    # تقریب خیلی ساده بر اساس عرض جغرافیایی ایران
    if lat is not None:
        if lat >= 36:
            return 5.0
        if lat >= 33:
            return 4.2
        if lat >= 30:
            return 3.5
        return 2.8
    return _DEFAULT_DECLINATION_IR


def _format_distance(km: float) -> str:
    if km >= 100:
        return f"{km:,.0f} کیلومتر"
    return f"{km:,.1f} کیلومتر"


def _resolve_city_coords(city: str) -> Optional[Tuple[float, float]]:
    if not city:
        return None
    c = str(city).strip()
    if c in CITY_COORDS:
        return tuple(CITY_COORDS[c][:2])  # type: ignore
    # جستجوی نرم
    for k, v in CITY_COORDS.items():
        if k in c or c in k:
            return tuple(v[:2])  # type: ignore
    return None


def compute_qibla(
    lat: float,
    lon: float,
    *,
    label: str = "",
    city: Optional[str] = None,
) -> dict:
    """محاسبه خام قبله برای یک مختصات."""
    bearing = _bearing_true(lat, lon, KAABA_LAT, KAABA_LON)
    distance = _haversine_km(lat, lon, KAABA_LAT, KAABA_LON)
    decl = _declination_for(city, lat)
    # زاویه تقریبی برای قطب‌نمای مغناطیسی:
    # bearing_magnetic ≈ bearing_true - declination  (وقتی decl شرقی باشد)
    magnetic = (bearing - decl + 360.0) % 360.0
    return {
        "lat": lat,
        "lon": lon,
        "label": label or city or f"{lat:.4f}, {lon:.4f}",
        "city": city or "",
        "bearing_true": bearing,
        "bearing_magnetic": magnetic,
        "declination": decl,
        "direction": _cardinal_name(bearing),
        "distance_km": distance,
        "from_gps": False,
    }


def format_qibla_message(data: dict) -> str:
    """ساخت متن کامل خروجی برای تلگرام."""
    label = data.get("label") or "موقعیت شما"
    bearing = float(data["bearing_true"])
    magnetic = float(data["bearing_magnetic"])
    decl = float(data["declination"])
    direction = data["direction"]
    dist = _format_distance(float(data["distance_km"]))
    from_gps = bool(data.get("from_gps"))

    source_line = (
        "📍 بر اساس **موقعیت لحظه‌ای** که فرستادی"
        if from_gps
        else f"📍 بر اساس مختصات شهر **{label}**"
    )

    return (
        f"🕋 **قبله‌نما — {label}**\n\n"
        f"{source_line}\n\n"
        f"📐 زاویه از شمال حقیقی: **{bearing:.1f}°**\n"
        f"🧭 جهت تقریبی: **{direction}**\n"
        f"📏 فاصله تا کعبه: **{dist}**\n\n"
        f"📌 **چطور با قطب‌نما بایستم؟**\n"
        f"۱) قطب‌نما یا قبله‌نمای گوشی را باز کن و دور از فلز نگه دار.\n"
        f"۲) عقربه/شاخص را با **شمال** هم‌راستا کن.\n"
        f"۳) بدن را **ساعت‌گرد** بچرخان تا به حدود **{bearing:.0f}°** برسی.\n"
        f"۴) همان سمت، قبله است (تقریباً {direction}).\n\n"
        f"⚠️ **شمال مغناطیسی ≠ شمال حقیقی**\n"
        f"زاویه بالا نسبت به شمال جغرافیایی (حقیقی) است.\n"
        f"میل مغناطیسی تقریبی این ناحیه حدود **{decl:.1f}° شرقی** است؛\n"
        f"برای قطب‌نمای مغناطیسی ساده می‌توانی حدود **{magnetic:.0f}°** را هدف بگیری.\n"
        f"دقیق‌ترین مرجع روزمره: **محراب مسجد محل** یا قبله‌نمای GPS گوشی.\n\n"
        f"💡 برای دقت نقطه‌ای، موقعیت فعلی‌ات را از تلگرام بفرست "
        f"(دکمه 📎 → موقعیت مکانی / Location)."
    )


def qibla_direction(city: str) -> str:
    """API سازگار با نسخه قبلی — از نام شهر."""
    city = (city or "").strip() or "قم"
    coords = _resolve_city_coords(city)
    if not coords:
        return (
            f"❌ شهر «{city}» پیدا نشد. ابتدا شهر را از منوی تنظیمات انتخاب کن،\n"
            f"یا موقعیت لحظه‌ای‌ات را برای قبله دقیق بفرست."
        )
    data = compute_qibla(coords[0], coords[1], label=city, city=city)
    return format_qibla_message(data)


def qibla_from_coords(
    lat: float,
    lon: float,
    *,
    label: str = "موقعیت شما",
) -> str:
    """قبله از مختصات GPS / لوکیشن تلگرام."""
    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except (TypeError, ValueError):
        return "❌ مختصات نامعتبر است."
    if not (-90 <= lat_f <= 90 and -180 <= lon_f <= 180):
        return "❌ مختصات خارج از بازه معتبر است."
    data = compute_qibla(lat_f, lon_f, label=label, city=None)
    data["from_gps"] = True
    return format_qibla_message(data)


def qibla_location_keyboard():
    """کیبورد درخواست موقعیت برای قبله دقیق‌تر.

    استفاده در handler:
        from bot.features.religious.qibla import qibla_location_keyboard
        await update.message.reply_text(..., reply_markup=qibla_location_keyboard())
    """
    try:
        from telegram import KeyboardButton, ReplyKeyboardMarkup

        return ReplyKeyboardMarkup(
            [
                [KeyboardButton("📍 ارسال موقعیت برای قبله دقیق", request_location=True)],
                [KeyboardButton("🔙 بازگشت به مذهبی")],
            ],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
    except Exception:
        return None


def qibla_direction_with_prompt(city: str) -> tuple[str, object]:
    """متن قبله + کیبورد درخواست لوکیشن (برای handlerهای جدید)."""
    text = qibla_direction(city)
    kb = qibla_location_keyboard()
    return text, kb
