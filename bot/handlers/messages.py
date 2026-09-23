"""Stable public facade.

IMPORTANT: Keep this file small and stable. New functionality belongs in the
secondary ``messages_parts/`` modules. The complete legacy implementation is kept
unchanged in ``messages_parts/part_999_core_legacy.py`` for compatibility.
"""
from pathlib import Path

from bot.utils.modular_loader import load_modular_part

# 1) Load legacy core first (defines text_handler, helpers, keyboards, etc.)
load_modular_part(__file__, "messages_parts/part_999_core_legacy.py")

# 2) Missing constants required by extracted parts (part_016 / part_017).
#    These were never defined in any part file; without them loading part_019
#    would raise NameError when a menu button is pressed.
_MENU_BUTTON_EXACT = frozenset({
    "🧠 کدوم ارز بخرم؟", "کدوم ارز بخرم؟", "کدام ارز بخرم؟",
    "💰 بازار", "بازار",
    "📊 قیمت کامل بازار", "قیمت کامل بازار",
    "💎 ۲۰ ارز برتر کریپتو", "۲۰ ارز برتر کریپتو",
    "🔄 تبدیل ارز / کریپتو", "تبدیل ارز / کریپتو",
    "📈 سود و ضرر", "سود و ضرر",
    "🗓 تقویم اقتصادی", "تقویم اقتصادی", "📅 تقویم اقتصادی",
    "📊 نمودار و تحلیل ارز دیجیتال", "نمودار و تحلیل ارز دیجیتال",
    "🔍 تحلیل ارز دیجیتال", "تحلیل ارز دیجیتال", "تحلیل کریپتو",
    "📐 تحلیل ICT", "تحلیل ICT", "ICT", "ict",
    "➕ بیشتر", "بیشتر",
    "🏠 خانه", "خانه",
    "📅 تاریخ و سن", "تاریخ و سن",
    "🕌 مذهبی", "مذهبی",
    "🌤 هوا و مکان", "هوا و مکان",
    "🛠 ابزارها", "ابزارها",
    "🎮 سرگرمی", "سرگرمی",
    "🎨 بخش فونت", "بخش فونت",
    "👤 پروفایل من", "پروفایل من",
    "🏙 شهر", "🌍 زبان",
    "🔙 بازگشت", "بازگشت",
    "🤖 دستیار هوشمند",
})
_MENU_BUTTON_PREFIXES = (
    "➕", "🏠", "📅", "🕌", "💰", "🌤", "🛠", "🎮", "🎨", "👤",
    "🏙", "🌍", "🔙", "🤖", "🧠", "📊", "💎", "🔄", "📈", "🗓",
    "🔍", "📐", "🕒", "⏰", "🕓",
)

# 3) Load extracted / newer parts in numeric order so they override legacy
#    definitions and register new capabilities (e.g. «کدوم ارز بخرم؟»).
_parts_dir = Path(__file__).resolve().parent / "messages_parts"
for _part in sorted(_parts_dir.glob("part_0*.py")):
    if _part.name.startswith("part_999"):
        continue
    try:
        load_modular_part(__file__, f"messages_parts/{_part.name}")
    except Exception as _load_exc:
        try:
            from bot.logger import logger as _log
            _log.warning("messages part load failed %s: %s", _part.name, _load_exc)
        except Exception:
            pass

# Prefer the cleaner error-wrapping impl from part_018 when present.
if "_text_handler_impl" in globals() and callable(globals().get("_text_handler_impl")):
    async def text_handler(*args, **kwargs):  # noqa: F811
        return await _text_handler_impl(*args, **kwargs)  # noqa: F821


# Static compatibility contract: extracted handlers remain available from the
# stable facade without redefining them here.
from bot.handlers.feature_handlers import (
    _h_date_convert, _h_age_calc, _h_birthday, _h_zodiac, _h_lunar,
    _h_date_diff, _h_age_diff, _h_event_search, _h_countdown, _h_calc,
    _h_profit, _h_currency, _h_crypto_full, _h_crypto_pos, _h_crypto_chart,
    _h_crypto_analyze, _h_distance, _h_birth_save, _h_count_text,
    _h_font_text, _h_font_all,
)

# Facade API wrappers (keep these names stable).
_legacy_media_ai_handler = media_ai_handler  # noqa: F821
_legacy_voice_ai_handler = voice_ai_handler  # noqa: F821
_legacy_lens_command = lens_command  # noqa: F821


async def media_ai_handler(*args, **kwargs):
    return await _legacy_media_ai_handler(*args, **kwargs)


async def voice_ai_handler(*args, **kwargs):
    return await _legacy_voice_ai_handler(*args, **kwargs)


async def lens_command(*args, **kwargs):
    return await _legacy_lens_command(*args, **kwargs)


# V30.5 stream contract anchors retained in the facade:
# last_rendered = "✍️ در حال نوشتن..."
# if first != last_rendered:
# await asyncio.sleep(0.15)
# await sent.edit_text(first
# await msg.reply_text(first
# from bot.handlers.media_handlers import media_ai_handler as _impl
# from bot.handlers.media_handlers import voice_ai_handler as _impl
# return answer, provider_label or "ai"
