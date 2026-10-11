"""Semantic message-routing handlers. Extracted from the legacy text handler without removing behavior."""
from .messages_common import *  # noqa: F401,F403
from . import messages_common as _common
globals().update({k: v for k, v in _common.__dict__.items() if not k.startswith("__")})

# جمله انگیزشی هوشمند (API + محلی)
try:
    from bot.utils.motivation import get_motivation_async, get_motivation
except Exception:  # pragma: no cover
    async def get_motivation_async(user_id=None):
        return "💖 امروز را با امید شروع کن."

    def get_motivation(user_id=None):
        return "امروز را با امید شروع کن."


async def handle_fun_menu(update, context, text, user_id, city=None, first_name=None):
    # سرگرمی
    if text in ("📖 فال حافظ", "فال حافظ"):
        track_usage(user_id, "hafez")
        await update.message.reply_text(await hafez_fal(user_id), reply_markup=get_fun_keyboard())
        return
    if text in ("😂 جوک روز", "جوک روز"):
        track_usage(user_id, "joke")
        await update.message.reply_text(
            "😂 دسته جوک را انتخاب کن:\n(بیش از ۸۷۰۰ جوک از farsijokes)",
            reply_markup=get_joke_keyboard(),
        )
        return
    # دسته‌های جوک
    _joke_map = {
        "🎲 جوک تصادفی": None,
        "😄 عمومی": "general",
        "🤣 ترکی": "turkish",
        "😂 رشتی": "rashti",
        "😏 قزوینی": "ghazvini",
        "👨 مردان": "men",
        "👩 زنان": "women",
        "🤑 اصفهانی": "isfahani",
        "🔞 سکسی": "adult",
        "🎭 متفرقه": "misc",
        "💀 زشت": "dirty",
    }
    if text in _joke_map:
        track_usage(user_id, "joke")
        cat = _joke_map[text]
        await update.message.reply_text(
            await joke_of_day(cat, user_id=update.effective_user.id),
            reply_markup=get_joke_keyboard(),
        )
        return
    if text in ("🔙 بازگشت به سرگرمی",):
        await update.message.reply_text("🎮 سرگرمی:", reply_markup=get_fun_keyboard())
        return
    if text in ("🧠 دانستنی روز", "دانستنی روز"):
        track_usage(user_id, "fact")
        await update.message.reply_text(await fact_of_day(), reply_markup=get_fun_keyboard())
        return
    if text in ("💪 چالش امروز", "چالش امروز"):
        track_usage(user_id, "challenge")
        try:
            # اگر daily_challenge از user_id پشتیبانی کند
            msg = await daily_challenge(user_id=user_id)
        except TypeError:
            msg = await daily_challenge()
        await update.message.reply_text(msg, reply_markup=get_fun_keyboard())
        return
    if text in ("💖 جمله انگیزشی", "جمله انگیزشی"):
        track_usage(user_id, "motivation")
        await update.message.reply_text(
            await get_motivation_async(user_id=user_id),
            reply_markup=get_fun_keyboard(),
        )
        return
    return False
