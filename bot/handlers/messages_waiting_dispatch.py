"""Semantic message-routing handlers. Extracted from the legacy text handler without removing behavior."""
from .messages_common import *  # noqa: F401,F403
from . import messages_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})

def _is_back(text):
    t = text.strip()
    return t in ("🔙 بازگشت", "بازگشت") or "بازگشت" in t

def _is_back_more(text):
    return "بازگشت به بیشتر" in text

async def handle_waiting_dispatch(update, context, text, user_id, city=None, first_name=None, *_args, **_kwargs):
    waiting = context.user_data.get("waiting_for")
    if waiting:
        if _is_back(text) or _is_back_more(text):
            context.user_data.pop("waiting_for", None)
            await update.message.reply_text("➕ منوی بیشتر:", reply_markup=get_more_keyboard())
            return
        # اگر کاربر دکمه منو زد، waiting را رها کن و ادامه بده
        menu_starts = (
            "➕", "🏠", "📅", "🕌", "💰", "🌤", "🛠", "🎮", "🎨", "👤",
            "🏙", "🌍", "🔙", "💵", "💎", "🔄", "📈", "📐", "🔢", "🔐",
            "📝", "🗺", "⏰", "📒", "📖", "😂", "🧠", "💪", "💖", "🕋",
            "📿", "🙏", "🔔", "🌫", "📍", "🇬🇧", "🇮🇷", "🌈", "📋", "🤖", "🧹",
        )
        if text.startswith(menu_starts) or text in (
            "بیشتر", "بازار", "مذهبی", "ابزارها", "سرگرمی", "فونت", "پروفایل",
            "تاریخ و سن", "هوا و مکان", "انتخاب شهر", "تقویم", "زبان",
        ):
            context.user_data.pop("waiting_for", None)
            waiting = None
        else:
            handlers = {
                "date_convert": _h_date_convert, "age_calc": _h_age_calc,
                "birthday": _h_birthday, "zodiac": _h_zodiac, "lunar": _h_lunar,
                "date_diff": _h_date_diff, "age_diff": _h_age_diff,
                "event_search": _h_event_search, "countdown": _h_countdown,
                "calc": _h_calc,
                "profit": _h_profit, "currency": _h_currency, "distance": _h_distance, "crypto_chart": _h_crypto_full, "crypto_analyze": _h_crypto_full, "crypto_full": _h_crypto_full, "crypto_pos": _h_crypto_pos, "crypto_alert": _h_crypto_pos,
                "birth_save": _h_birth_save,
                "count_text": _h_count_text,
                "font_text": _h_font_text, "font_all": _h_font_all,
                "economic_calendar": _h_economic_calendar,
            }
            fn = handlers.get(waiting)
            if fn:
                try:
                    await fn(update, context, text, user_id)
                except Exception as e:
                    logger.error(f"waiting handler {waiting}: {e}", exc_info=True)
                    context.user_data.pop("waiting_for", None)
                    await update.message.reply_text(
                        "⚠️ خطا در پردازش. دوباره از منو انتخاب کنید.",
                        reply_markup=get_more_keyboard(),
                    )
                return
            context.user_data.pop("waiting_for", None)
    return False
