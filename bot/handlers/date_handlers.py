"""Domain-specific Telegram handlers for date tools — UI/UX بهبودیافته."""
from bot.database import set_birth_date
from bot.utils.helpers import get_date_tools_keyboard
from bot.features.date.features_date_date_tools import (
    parse_shamsi,
    parse_any_date,
    parse_two_dates,
    parse_countdown,
    birthday_countdown,
    zodiac_animal,
    lunar_age,
    date_diff,
    age_diff,
    convert_with_weekday,
    search_events,
    custom_countdown,
)
from bot.features.date.features_date_converters import calculate_age, parse_birth_datetime


def _kb():
    return get_date_tools_keyboard()


def _invalid(kind: str) -> str:
    tips = {
        "date": "تاریخ نامعتبر است." + chr(10) + "مثال درست: `1403/05/18` یا `2024/08/09`",
        "birth": "تاریخ تولد نامعتبر است." + chr(10) + "مثال: `1375/03/15`",
        "two": "دو تاریخ شمسی لازم است." + chr(10) + "مثال: `1375/03/15 1403/05/18`",
        "countdown": "فرمت شمارش‌معکوس نامعتبر است." + chr(10) + "مثال: `1405/01/01 نوروز`",
        "event": "کلمه کلیدی خالی یا نامعتبر است." + chr(10) + "مثال: `نوروز`",
    }
    tip = tips.get(kind, "ورودی نامعتبر است. دوباره بفرست.")
    return chr(10).join([
        "❌  **ورودی نامعتبر**",
        "・ ・ ・ ・ ・",
        tip,
        "",
        "・ ・ ・ ・ ・",
        "💡 دوباره بفرست؛ لازم نیست به منو برگردی.",
    ])


async def _h_date_convert(u, c, t, uid):
    c.user_data["waiting_for"] = "date_convert"
    p = parse_any_date(t)
    if not p:
        await u.message.reply_text(_invalid("date"), reply_markup=_kb(), parse_mode="Markdown")
        return
    await u.message.reply_text(convert_with_weekday(*p), reply_markup=_kb())


async def _h_age_calc(u, c, t, uid):
    c.user_data["waiting_for"] = "age_calc"
    p = parse_birth_datetime(t)
    if not p:
        await u.message.reply_text(_invalid("birth"), reply_markup=_kb(), parse_mode="Markdown")
        return
    await u.message.reply_text(calculate_age(*p), reply_markup=_kb())


async def _h_birthday(u, c, t, uid):
    c.user_data["waiting_for"] = "birthday"
    p = parse_shamsi(t)
    if p:
        y, m, d = p[0], p[1], p[2]
        set_birth_date(uid, f"{y}/{m}/{d}")
        await u.message.reply_text(birthday_countdown(y, m, d), reply_markup=_kb())
    else:
        await u.message.reply_text(_invalid("birth"), reply_markup=_kb(), parse_mode="Markdown")


async def _h_zodiac(u, c, t, uid):
    c.user_data["waiting_for"] = "zodiac"
    p = parse_shamsi(t)
    if not p:
        await u.message.reply_text(_invalid("birth"), reply_markup=_kb(), parse_mode="Markdown")
        return
    await u.message.reply_text(zodiac_animal(p[0], p[1], p[2]), reply_markup=_kb())


async def _h_lunar(u, c, t, uid):
    c.user_data["waiting_for"] = "lunar"
    p = parse_shamsi(t)
    if not p:
        await u.message.reply_text(_invalid("birth"), reply_markup=_kb(), parse_mode="Markdown")
        return
    await u.message.reply_text(lunar_age(p[0], p[1], p[2]), reply_markup=_kb())


async def _h_date_diff(u, c, t, uid):
    c.user_data["waiting_for"] = "date_diff"
    p = parse_two_dates(t)
    if not p:
        await u.message.reply_text(_invalid("two"), reply_markup=_kb(), parse_mode="Markdown")
        return
    await u.message.reply_text(date_diff(*p[0], *p[1]), reply_markup=_kb())


async def _h_age_diff(u, c, t, uid):
    c.user_data["waiting_for"] = "age_diff"
    p = parse_two_dates(t)
    if not p:
        await u.message.reply_text(_invalid("two"), reply_markup=_kb(), parse_mode="Markdown")
        return
    await u.message.reply_text(age_diff(*p[0], *p[1]), reply_markup=_kb())


async def _h_event_search(u, c, t, uid):
    c.user_data["waiting_for"] = "event_search"
    q = (t or "").strip()
    if not q:
        await u.message.reply_text(_invalid("event"), reply_markup=_kb(), parse_mode="Markdown")
        return
    await u.message.reply_text(search_events(q), reply_markup=_kb())


async def _h_countdown(u, c, t, uid):
    c.user_data["waiting_for"] = "countdown"
    p = parse_countdown(t)
    if not p:
        await u.message.reply_text(_invalid("countdown"), reply_markup=_kb(), parse_mode="Markdown")
        return
    await u.message.reply_text(custom_countdown(*p), reply_markup=_kb())
