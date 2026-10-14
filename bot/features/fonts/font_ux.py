"""UX فونت — کیبورد اینلاین، پیش‌نمایش، اقدامات بعد از تبدیل."""
from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.features.fonts.converter import (
    EN_STYLES,
    FA_STYLES,
    apply_font,
    apply_all_fonts,
    _apply,
)
from bot.features.fonts.styles import FONT_NAMES, STYLES
from bot.utils.helpers import get_font_keyboard

try:
    from bot.logger import logger
except Exception:  # pragma: no cover
    class _L:
        def debug(self, *a, **k): pass
        def error(self, *a, **k): pass
    logger = _L()

_BTN = InlineKeyboardButton


def _short_name(key: str) -> str:
    name = FONT_NAMES.get(key, key)
    # کوتاه برای دکمه
    name = name.replace(" (ضخیم)", "").replace(" (ایتالیک)", "")
    name = name.replace(" (دست‌نویس)", "").replace(" (گوتیک)", "").replace(" (دوبل)", "")
    return (name[:18] + "…") if len(name) > 19 else name


def font_studio_text() -> str:
    return "\n".join([
        "🎨  <b>استودیوی فونت</b>",
        "・ ・ ・ ・ ・",
        "",
        "🇬🇧 انگلیسی — استایل یونیکد",
        "🇮🇷 فارسی — تزئینی و سازگار",
        "🌈 همه فونت‌ها — یک متن روی همه",
        "📋 لیست — پیش‌نمایش سریع",
        "",
        "・ ・ ・ ・ ・",
        "از منو انتخاب کن یا از دکمه‌های زیر:",
    ])


def font_studio_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            _BTN("🇬🇧 انگلیسی", callback_data="font:menu:en"),
            _BTN("🇮🇷 فارسی", callback_data="font:menu:fa"),
        ],
        [
            _BTN("🌈 همه فونت‌ها", callback_data="font:menu:all"),
            _BTN("📋 لیست", callback_data="font:menu:list"),
        ],
    ])


def _style_grid(keys: list[str], prefix: str) -> InlineKeyboardMarkup:
    """شبکه انتخاب فونت با callback font:pick:<key>."""
    rows = []
    row = []
    for k in keys:
        if k not in STYLES:
            continue
        # پیش‌نمایش خیلی کوتاه روی لیبل
        try:
            prev = _apply("Aa", k)[:8]
        except Exception:
            prev = ""
        label = f"{_short_name(k)}"
        if prev and prev != "Aa":
            label = f"{_short_name(k)}"
        row.append(_BTN(label, callback_data=f"font:pick:{k}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([
        _BTN("🔙 استودیو", callback_data="font:menu:home"),
        _BTN("🌈 همه", callback_data="font:menu:all"),
    ])
    return InlineKeyboardMarkup(rows)


def font_en_inline() -> InlineKeyboardMarkup:
    return _style_grid(EN_STYLES, "en")


def font_fa_inline() -> InlineKeyboardMarkup:
    return _style_grid(FA_STYLES[:40], "fa")  # محدود برای شلوغ نشدن


def font_result_inline(style_key: str | None = None) -> InlineKeyboardMarkup:
    rows = [
        [
            _BTN("✍️ متن جدید", callback_data="font:again"),
            _BTN("🔀 عوض کردن فونت", callback_data="font:change"),
        ],
        [
            _BTN("🌈 همه استایل‌ها", callback_data="font:runall"),
            _BTN("🏠 استودیو", callback_data="font:menu:home"),
        ],
    ]
    return InlineKeyboardMarkup(rows)


def _ask_text_html(style_key: str) -> str:
    name = FONT_NAMES.get(style_key, style_key)
    try:
        sample = _apply("Hello / سلام", style_key)
    except Exception:
        sample = ""
    lines = [
        "🎨  <b>فونت آماده است</b>",
        f"✨  <code>{name}</code>",
        "・ ・ ・ ・ ・",
    ]
    if sample:
        lines.append(f"👁 نمونه: {sample}")
        lines.append("")
    lines.append("📝 متنت را همین‌جا بفرست.")
    lines.append("می‌توانی چند بار پشت‌سرهم بفرستی.")
    return "\n".join(lines)


def _result_html(text: str, style_key: str) -> str:
    """نتیجه با بلوک code برای کپی تک‌ضربه‌ای در تلگرام."""
    raw = apply_font(text, style_key)
    # rebuild with HTML
    if not text or not str(text).strip():
        return "❌ متن خالی است."
    text = str(text).strip()[:500]
    if style_key not in STYLES:
        return f"❌ فونت پیدا نشد."
    converted = _apply(text, style_key)
    name = FONT_NAMES.get(style_key, style_key)
    # escape html minimal
    def esc(s: str) -> str:
        return (
            s.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
    return "\n".join([
        "🎨  <b>نتیجهٔ فونت</b>",
        f"✨  <code>{esc(name)}</code>",
        "・ ・ ・ ・ ・",
        "",
        f"<code>{esc(converted)}</code>",
        "",
        "・ ・ ・ ・ ・",
        f"📥 اصل: {esc(text)}",
        "",
        "💡 روی متن بالا بزن تا کپی شود.",
    ])


def _all_html(text: str) -> str:
    body = apply_all_fonts(text)
    # convert markdown-ish to plain + code first line
    # simpler: wrap apply_all output lightly
    text = (text or "").strip()[:80]
    if not text:
        return apply_all_fonts(text)
    # rebuild gallery with HTML code blocks
    from bot.features.fonts.converter import _is_mostly_persian
    keys = FA_STYLES if _is_mostly_persian(text) else EN_STYLES
    lang = "فارسی / عربی" if keys is FA_STYLES else "انگلیسی"

    def esc(s: str) -> str:
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    lines = [
        "🌈  <b>گالری فونت</b>",
        f"📝  <code>{esc(text)}</code>",
        f"🌍  {lang}",
        "・ ・ ・ ・ ・",
        "",
    ]
    n = 0
    for k in keys:
        if k not in STYLES:
            continue
        try:
            conv = _apply(text, k)
            name = FONT_NAMES.get(k, k)
            n += 1
            lines.append(f"<b>{n}. {esc(name)}</b>")
            lines.append(f"<code>{esc(conv)}</code>")
            lines.append("")
        except Exception:
            continue
    lines.append("・ ・ ・ ・ ・")
    lines.append(f"✨  {n} استایل · روی هر کدام بزن تا کپی شود")
    return "\n".join(lines)


async def start_font_studio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("waiting_for", None)
    msg = update.effective_message
    if not msg:
        return
    await msg.reply_text(
        font_studio_text(),
        reply_markup=font_studio_inline(),
        parse_mode="HTML",
    )
    # reply keyboard هم بماند برای عادت کاربر
    await msg.reply_text(
        "منوی فونت فعال است.",
        reply_markup=get_font_keyboard(),
    )


async def font_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data or not query.data.startswith("font:"):
        return
    data = query.data
    parts = data.split(":")
    action = parts[1] if len(parts) > 1 else ""

    try:
        await query.answer()
    except Exception:
        pass

    async def _edit(text: str, kb=None):
        try:
            await query.edit_message_text(
                text,
                reply_markup=kb,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
        except Exception as e:
            logger.debug("font edit: %s", e)
            if query.message:
                await query.message.reply_text(
                    text, reply_markup=kb, parse_mode="HTML"
                )

    if action == "menu":
        sub = parts[2] if len(parts) > 2 else "home"
        if sub == "home":
            context.user_data.pop("waiting_for", None)
            await _edit(font_studio_text(), font_studio_inline())
        elif sub == "en":
            await _edit(
                "\n".join([
                    "🇬🇧  <b>فونت انگلیسی</b>",
                    "・ ・ ・ ・ ・",
                    "یک استایل را لمس کن.",
                ]),
                font_en_inline(),
            )
        elif sub == "fa":
            await _edit(
                "\n".join([
                    "🇮🇷  <b>فونت فارسی / عربی</b>",
                    "・ ・ ・ ・ ・",
                    "یک استایل سازگار را لمس کن.",
                ]),
                font_fa_inline(),
            )
        elif sub == "all":
            context.user_data["waiting_for"] = "font_all"
            context.user_data.pop("selected_font", None)
            await _edit(
                "\n".join([
                    "🌈  <b>گالری همه فونت‌ها</b>",
                    "・ ・ ・ ・ ・",
                    "یک کلمه یا جمله <b>کوتاه</b> بفرست.",
                    "مثال: <code>سلام</code> یا <code>Hello</code>",
                ]),
                InlineKeyboardMarkup([[_BTN("🔙 استودیو", callback_data="font:menu:home")]]),
            )
        elif sub == "list":
            from bot.features.fonts.converter import list_fonts
            # list_fonts is markdown-ish — send as plain via HTML escape
            txt = list_fonts().replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            txt = txt.replace("**", "").replace("`", "")
            await _edit(
                txt[:3500],
                InlineKeyboardMarkup([
                    [_BTN("🇬🇧 انگلیسی", callback_data="font:menu:en"),
                     _BTN("🇮🇷 فارسی", callback_data="font:menu:fa")],
                    [_BTN("🔙 استودیو", callback_data="font:menu:home")],
                ]),
            )
        return

    if action == "pick" and len(parts) > 2:
        key = parts[2]
        if key not in STYLES:
            await _edit("❌ این فونت در دسترس نیست.")
            return
        context.user_data["selected_font"] = key
        context.user_data["waiting_for"] = "font_text"
        await _edit(
            _ask_text_html(key),
            InlineKeyboardMarkup([
                [_BTN("🔀 فونت دیگر", callback_data="font:change")],
                [_BTN("🔙 استودیو", callback_data="font:menu:home")],
            ]),
        )
        return

    if action == "again":
        key = context.user_data.get("selected_font") or "bold"
        context.user_data["waiting_for"] = "font_text"
        context.user_data["selected_font"] = key
        await _edit(
            _ask_text_html(key),
            InlineKeyboardMarkup([
                [_BTN("🔀 فونت دیگر", callback_data="font:change")],
                [_BTN("🔙 استودیو", callback_data="font:menu:home")],
            ]),
        )
        return

    if action == "change":
        # اگر آخرین متن فارسی بود، FA نشان بده
        last = context.user_data.get("font_last_text") or ""
        fa_chars = sum(1 for ch in last if "\u0600" <= ch <= "\u06FF")
        if fa_chars >= max(1, len(last) // 3):
            await _edit(
                "🇮🇷  <b>تعویض فونت فارسی</b>\n・ ・ ・ ・ ・\nاستایل جدید را انتخاب کن.",
                font_fa_inline(),
            )
        else:
            await _edit(
                "🇬🇧  <b>تعویض فونت</b>\n・ ・ ・ ・ ・\nاستایل جدید را انتخاب کن.",
                font_en_inline(),
            )
        return

    if action == "runall":
        last = context.user_data.get("font_last_text")
        if last:
            context.user_data["waiting_for"] = "font_all"
            await _edit(_all_html(last), font_result_inline())
        else:
            context.user_data["waiting_for"] = "font_all"
            await _edit(
                "🌈 متن کوتاه بفرست تا همه استایل‌ها اعمال شود.",
                InlineKeyboardMarkup([[_BTN("🔙 استودیو", callback_data="font:menu:home")]]),
            )
        return


async def handle_font_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """خروجی تبدیل با UX اینلاین."""
    style = context.user_data.get("selected_font") or "bold"
    context.user_data["font_last_text"] = text
    context.user_data["waiting_for"] = "font_text"
    await update.message.reply_text(
        _result_html(text, style),
        reply_markup=font_result_inline(style),
        parse_mode="HTML",
    )


async def handle_font_all(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    context.user_data["font_last_text"] = text
    context.user_data["waiting_for"] = "font_all"
    await update.message.reply_text(
        _all_html(text),
        reply_markup=font_result_inline(),
        parse_mode="HTML",
    )
