"""قالب یکدست UI پاسخ‌های گروه."""
from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def hr() -> str:
    return "━━━━━━━━━━━━━━"


def card(title: str, body: str, *, footer: str | None = None) -> str:
    title = (title or "").strip()
    body = (body or "").strip()
    parts = []
    if title:
        parts.append(title)
        parts.append(hr())
    if body:
        parts.append(body)
    if footer:
        parts.append(hr())
        parts.append(footer)
    return "\n".join(parts)


def price_card(label: str, value: str, *, source: str = "") -> str:
    body = f"نرخ: <b>{value}</b>"
    if source:
        body += f"\n<i>منبع: {source}</i>"
    return card(f"💵 <b>{label}</b>", body)


def weather_card(city: str, body: str) -> str:
    return card(f"🌤️ <b>آب‌وهوا · {city}</b>", body)


def shop_card(body: str) -> str:
    return card("🛒 <b>نتایج خرید</b>", body)


def shop_fallback(query: str) -> str:
    from urllib.parse import quote
    q = quote((query or "").strip()[:80])
    body = (
        "الان نتیجهٔ زنده از فروشگاه کامل نبود.\n"
        f"🔎 <a href=\"https://torob.com/search/?query={q}\">جستجو در ترب</a>\n"
        f"🛍 <a href=\"https://www.digikala.com/search/?q={q}\">جستجو در دیجی‌کالا</a>"
    )
    return card("🛒 <b>جستجوی خرید</b>", body)


def ai_footer() -> str:
    return "💡 ریپلای کن یا منشن کن تا ادامه بدیم"


def group_help_text() -> str:
    return card(
        "👋 <b>من اینجام</b>",
        "• قیمت دلار\n"
        "• هوای قم\n"
        "• ربات ساعت تا ۵۰۰ هزار پیدا کن\n"
        "• روی عکس Reply: ربات اینو تحلیل کن\n"
        "• /ask سؤال آزاد\n"
        "• /groupsettings تنظیمات ادمین",
    )


def continue_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("ادامه", callback_data="group_more"),
                InlineKeyboardButton("بستن", callback_data="group_dismiss"),
            ]
        ]
    )
