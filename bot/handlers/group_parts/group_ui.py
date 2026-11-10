"""UI/UX حرفه‌ای پاسخ‌های گروه — قالب یکدست، دکمه‌ها، کارت‌ها."""
from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from urllib.parse import quote


# ─── پایه ─────────────────────────────────────────────

def hr() -> str:
    return "────────────"


def esc(s: str) -> str:
    return (
        str(s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def card(title: str, body: str, *, footer: str | None = None) -> str:
    parts: list[str] = []
    if title:
        parts.append(title.strip())
        parts.append(hr())
    if body:
        parts.append(body.strip())
    if footer:
        parts.append(hr())
        parts.append(footer.strip())
    return "\n".join(parts)


def attr_line(user) -> str:
    if not user:
        return ""
    name = (getattr(user, "full_name", None) or getattr(user, "first_name", None) or "کاربر").strip()
    if len(name) > 22:
        name = name[:20] + "…"
    return f"<i>برای {esc(name)}</i>"


# ─── هدر / فوتر AI ───────────────────────────────────

def ai_header(user=None, *, streaming: bool = False) -> str:
    if streaming:
        return "🤖 <b>روز زیبا</b>\n" + hr() + "\n"
    name_bit = ""
    if user is not None:
        name = (getattr(user, "full_name", None) or getattr(user, "first_name", None) or "").strip()
        if name:
            if len(name) > 20:
                name = name[:18] + "…"
            name_bit = f" · {esc(name)}"
    return f"🤖 <b>روز زیبا</b>{name_bit}\n" + hr() + "\n"


def ai_footer() -> str:
    return "\n" + hr() + "\n💬 ریپلای یا منشن = ادامه"


def streaming_placeholder() -> str:
    return "در حال نوشتن…"


# ─── کارت‌های سریع ───────────────────────────────────

def price_card(label: str, value: str, *, source: str = "", extra: str = "") -> str:
    body = f"<b>{esc(value)}</b>"
    if extra:
        body += f"\n{extra}"
    if source:
        body += f"\n<i>{esc(source)}</i>"
    return card(f"💵 {esc(label)}", body)


def weather_card(city: str, lines: str) -> str:
    return card(f"🌤️ آب‌وهوا · {esc(city)}", lines)


def shop_card(body: str) -> str:
    return card("🛒 نتایج خرید", body)


def shop_links(query: str) -> str:
    q = quote((query or "").strip()[:80])
    label = esc((query or "").strip()[:50] or "جستجو")
    body = (
        f"برای «{label}»\n\n"
        f"🔎 <a href=\"https://torob.com/search/?query={q}\">ترب</a>"
        f"  ·  "
        f"🛍 <a href=\"https://www.digikala.com/search/?q={q}\">دیجی‌کالا</a>\n\n"
        "<i>برای قیمت لحظه‌ای روی لینک بزن</i>"
    )
    return card("🛒 خرید", body)


def analyze_card(title: str, body: str) -> str:
    return card(f"📊 {esc(title)}", body)


def help_card() -> str:
    body = (
        "<b>سریع</b>\n"
        "💵 قیمت دلار · طلا · بیتکوین\n"
        "🌤️ هوای تهران\n"
        "🛒 باتری ایفون پیدا کن\n"
        "📊 تحلیل طلا\n\n"
        "<b>هوشمند</b>\n"
        "عکس + کپشن: ربات اینو تحلیل کن\n"
        "لینک تیک‌تاک/اینستا → دانلود\n"
        "/ask سؤال آزاد\n\n"
        "🧠 حافظه گروه · خلاصه گروه\n\n"
        "<i>ادمین: /groupsettings</i>"
    )
    return card("👋 روز زیبا اینجاست", body)



def error_card(text: str = "الان نتونستم کامل جواب بدم. دوباره بپرس.") -> str:
    return card("⚠️", text)


# ─── کیبوردها ─────────────────────────────────────────

def kb_ai(user_id: int = 0) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("➕ ادامه", callback_data="ai_continue:0"),
                InlineKeyboardButton("👍", callback_data=f"gfb:up:{user_id}"),
                InlineKeyboardButton("👎", callback_data=f"gfb:dn:{user_id}"),
            ],
            [InlineKeyboardButton("بستن", callback_data="group_dismiss")],
        ]
    )


def kb_price() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🔄 دلار", callback_data="gquick:dollar"),
                InlineKeyboardButton("🥇 طلا", callback_data="gquick:gold"),
                InlineKeyboardButton("₿ BTC", callback_data="gquick:btc"),
            ]
        ]
    )


def kb_shop(query: str) -> InlineKeyboardMarkup:
    q = quote((query or "").strip()[:60])
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("ترب", url=f"https://torob.com/search/?query={q}"),
                InlineKeyboardButton("دیجی‌کالا", url=f"https://www.digikala.com/search/?q={q}"),
            ]
        ]
    )


def kb_help() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("💵 دلار", callback_data="gquick:dollar"),
                InlineKeyboardButton("🌤️ هوا", callback_data="gquick:weather"),
            ],
            [
                InlineKeyboardButton("🥇 طلا", callback_data="gquick:gold"),
                InlineKeyboardButton("₿ BTC", callback_data="gquick:btc"),
            ],
        ]
    )


def kb_dismiss() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("بستن", callback_data="group_dismiss")]])


def memory_card(stats: dict | None = None, preview: str = "") -> str:
    stats = stats or {}
    turns = stats.get("turns", 0)
    body = f"نوبت‌های ذخیره‌شده: <b>{turns}</b>"
    if preview:
        body += "\n\n<b>آخرین زمینه</b>\n" + preview[:700]
    body += "\n\n<code>خلاصه گروه</code> · <code>پاک کردن حافظه</code>"
    return card("🧠 حافظه گروه", body)


def summary_card(summary: str) -> str:
    return card("📚 خلاصه گروه", (summary or "خالی")[:3500])


def kb_memory() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📚 خلاصه", callback_data="gmem:summary"),
                InlineKeyboardButton("🗑 پاک کردن", callback_data="gmem:clear"),
            ],
            [InlineKeyboardButton("بستن", callback_data="group_dismiss")],
        ]
    )
