"""
Group Mode — پشتیبانی حرفه‌ای ربات در گروه‌ها و سوپرگروه‌ها.

قوانین UX گروه:
- هوشمند: سؤال و موضوعات مرتبط را بدون منشن هم تشخیص می‌دهد؛ چت معمولی را نادیده می‌گیرد.
- ReplyKeyboard استفاده نمی‌شود؛ فقط InlineKeyboard.
- پاسخ‌ها کوتاه‌تر، تمیزتر و با attribution هستند.
- ادمین گروه می‌تواند AI را فعال/غیرفعال کند.
"""
from __future__ import annotations

import re
from typing import Optional, Tuple

from telegram import Update, Chat, Message, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.constants import ChatType, ChatMemberStatus
from telegram.ext import ContextTypes

from bot.logger import logger
from bot.config import config


def normalize_persian_text(text: str) -> str:
    """Normalize common Arabic/Persian variants for intent matching only."""
    value = str(text or "")
    value = value.translate(str.maketrans({"ي": "ی", "ى": "ی", "ك": "ک", "ۀ": "ه", "ة": "ه", "ؤ": "و", "إ": "ا", "أ": "ا"}))
    value = re.sub(r"[\u064B-\u065F\u0670\u0640]", "", value)
    value = value.replace("\u200c", " ").replace("\u200f", "").replace("\u200e", "")
    value = re.sub(r"\s+", " ", value).strip()
    return value


def is_group_chat(chat: Optional[Chat]) -> bool:
    if not chat:
        return False
    return chat.type in (ChatType.GROUP, ChatType.SUPERGROUP)


def is_private_chat(chat: Optional[Chat]) -> bool:
    if not chat:
        return False
    return chat.type == ChatType.PRIVATE


def get_bot_username(context: ContextTypes.DEFAULT_TYPE) -> str:
    bot = context.bot
    uname = getattr(bot, "username", None) or getattr(config, "BOT_USERNAME", "") or ""
    return (uname or "").lstrip("@").lower()


def is_bot_mentioned(text: str, bot_username: str) -> bool:
    if not text or not bot_username:
        return False
    pattern = rf"(?<!\w)@{re.escape(bot_username)}(?!\w)"
    return bool(re.search(pattern, text, flags=re.IGNORECASE))


def is_reply_to_bot(message: Optional[Message], bot_id: int) -> bool:
    if not message or not message.reply_to_message:
        return False
    replied = message.reply_to_message
    if replied.from_user and replied.from_user.id == bot_id:
        return True
    return False


# الگوهای سؤال و درخواست که ربات باید جواب دهد (بدون منشن اجباری)
_QUESTION_MARKERS = re.compile(
    r"(?:"
    r"[?؟]"
    r"|^(?:آیا|چطور|چگونه|چرا|کی|کجا|کدام|چند|چه(?:‌| )?قدر|چی(?:ه)?|کیه|چیه)"
    r"|(?:چقدر|چندتا|چند تا|چی شد|چه خبر|چخبر)"
    r")",
    re.IGNORECASE,
)

# موضوعات و قابلیت‌هایی که ربات بلد است
_BOT_TOPICS = re.compile(
    r"(?:"
    r"قیمت|دلار|یورو|تومان|تومن|طلا|سکه|ارز|بورس|شاخص"
    r"|بیت‌?کوین|بیتکوین|اتریوم|رمزارز|کریپتو|تتر|btc|eth|usdt"
    r"|آب[‌ ]?و[‌ ]?هوا|هوای|دمای|باران|برف"
    r"|اذان|نماز|اوقات شرعی|قبله|استخاره|آیه|حدیث|اذکار"
    r"|تقویم|تاریخ|تبدیل تاریخ|سنم|زودیاک|برج"
    r"|دانلود|یوتیوب|اینستا|استوری"
    r"|تحلیل|rsi|حمایت|مقاومت|fear.?greed"
    r"|ساعت|منطقه زمانی|خلاصه مکالمه|خلاصه گفتگو|جمع بندی مکالمه|جمع بندی گفتگو"
    r"|ربات|هوشمند|دستیار|کمک کن|بگو|بگو ببینم|کاربرد|چیکار|چه‌کار|چه کار"
    r")",
    re.IGNORECASE,
)

# پیام‌های چت معمولی که نباید جواب داده شود
_IGNORE_CHAT = re.compile(
    r"^(?:"
    r"سلام|سلوم|درود|صبح بخیر|شب بخیر|خوبی|خوبم|مرسی|ممنون|ممنونم|عالی|آفرین"
    r"| Lol|hahaha|هههه|خخخ|😂+|🤣+|😅+|😊+|❤️+|👍+"
    r"|باشه|باش|اوکی|ok|okay|آها|آهان|هه|نمیخوام|بیخیال"
    r"|شب خوش|خداحافظ|بای|bye"
    r")[\s!.،,]*$",
    re.IGNORECASE,
)

# خطاب مستقیم به ربات بدون @
_DIRECT_ADDRESS = re.compile(
    r"(?:"
    r"^(?:ای )?ربات\b"
    r"|^(?:ای )?هوشمند\b"
    r"|بگو\s"
    r"|بهم بگو"
    r"|می‌(?:تو)?ونی\s"
    r"|میتونی\s"
    r"|کمک(?:م)?(?:\s|$)"
    r")",
    re.IGNORECASE,
)


def looks_like_bot_request(text: str) -> Tuple[bool, str]:
    """تشخیص هوشمند: آیا این پیام درخواست از ربات است یا چت معمولی گروه؟"""
    if not text:
        return False, "empty"
    t = normalize_persian_text(text)
    if len(t) < 2:
        return False, "too_short"
    if len(t) > 800:
        # پیام خیلی بلند معمولاً چت/کپی است نه سؤال سریع گروه
        if not _QUESTION_MARKERS.search(t[:200]) and not _BOT_TOPICS.search(t[:200]):
            return False, "too_long"

    if _IGNORE_CHAT.match(t):
        return False, "casual_chat"

    if _DIRECT_ADDRESS.search(t):
        return True, "direct_address"

    if _QUESTION_MARKERS.search(t) and _BOT_TOPICS.search(t):
        return True, "question_topic"

    # جملات موضوع‌محور بدون علامت سؤال، مثل «قیمت دلار» یا «هوای تهران»
    if _BOT_TOPICS.search(t) and len(t) <= 80:
        # حداقل یک کلمه معنادار غیر از salutation
        words = re.findall(r"[\w؀-ۿ]+", t)
        if len(words) >= 1:
            return True, "topic_phrase"

    return False, "no_intent"


def should_respond_in_group(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    allow_commands: bool = True,
) -> Tuple[bool, str]:
    """
    تصمیم هوشمند پاسخ در گروه.

    اولویت:
    1) دستور /  2) منشن  3) ریپلای به ربات  4) پیشوند
    5) تشخیص هوشمند سؤال/موضوع (بدون نیاز به منشن)
    """
    message = update.effective_message
    chat = update.effective_chat
    if not message or not chat or not is_group_chat(chat):
        return True, "private_or_unknown"

    text = normalize_persian_text(message.text or message.caption or "")
    bot_id = context.bot.id
    bot_uname = get_bot_username(context)

    # محدودیت‌های تنظیمات گروه
    try:
        from bot.handlers.group_settings import group_mention_only, group_admin_only, is_group_ai_enabled
        if not is_group_ai_enabled(chat.id):
            if allow_commands and text.startswith("/"):
                pass  # دستورات تنظیمات باید کار کنند
            else:
                return False, "ai_disabled"
        if group_admin_only(chat.id):
            # فقط در should_respond نمی‌توانیم await کنیم؛ چک سبک
            user = update.effective_user
            admin_ids = set(getattr(config, "ADMIN_IDS", []) or [])
            if user and user.id not in admin_ids:
                # ادمین تلگرام بودن در لایه handler چک می‌شود؛ اینجا فقط فلگ می‌گذاریم
                context.chat_data["group_admin_only"] = True
        if group_mention_only(chat.id):
            # فقط منشن / ریپلای / دستور
            if allow_commands and text.startswith("/"):
                return True, "command"
            if is_bot_mentioned(text, bot_uname):
                return True, "mention"
            if is_reply_to_bot(message, bot_id):
                return True, "reply"
            return False, "mention_only"
    except Exception as _se:
        logger.debug("group settings gate: %s", _se)

    if allow_commands and text.startswith("/"):
        return True, "command"

    if is_bot_mentioned(text, bot_uname):
        return True, "mention"

    if is_reply_to_bot(message, bot_id):
        return True, "reply"

    prefixes = getattr(config, "GROUP_TRIGGER_PREFIXES", ["!", "ربات", "هوشمند"])
    low = text.lower()
    for p in prefixes:
        p = (p or "").strip()
        if not p:
            continue
        if low.startswith(p.lower() + " ") or low == p.lower():
            return True, f"prefix:{p}"

    # حالت هوشمند: بدون منشن/دستور هم اگر سؤال یا موضوع مرتبط بود جواب بده
    smart_on = getattr(config, "GROUP_SMART_REPLY", True)
    if smart_on:
        ok, reason = looks_like_bot_request(text)
        if ok:
            return True, f"smart:{reason}"

    return False, "ignored"


def clean_group_prompt(text: str, bot_username: str) -> str:
    if not text:
        return ""
    cleaned = text
    if bot_username:
        cleaned = re.sub(
            rf"(?<!\w)@{re.escape(bot_username)}(?!\w)",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
    cleaned = re.sub(r"^(?:!|ربات|هوشمند)\s*", "", cleaned.strip(), flags=re.IGNORECASE)
    # حذف /ask و /ai از ابتدای متن
    cleaned = re.sub(r"^/(?:ask|ai)(?:@\w+)?\s*", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def group_attribution(user) -> str:
    if not user:
        return "کاربر"
    name = (user.full_name or user.first_name or "کاربر").strip()
    if len(name) > 28:
        name = name[:25] + "…"
    return name


def _esc(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def group_ai_header(user, *, streaming: bool = False) -> str:
    name = group_attribution(user)
    if streaming:
        return f"🤖 <b>روز زیبا</b> · پاسخ به <b>{_esc(name)}</b>\n━━━━━━━━━━━━━━\n"
    return f"🤖 <b>روز زیبا</b> · برای <b>{_esc(name)}</b>\n━━━━━━━━━━━━━━\n"


def group_ai_footer() -> str:
    return "\n━━━━━━━━━━━━━━\n💡 ریپلای کن یا منشن کن تا ادامه بدیم"


def group_inline_actions(user_id: int, answer_id: Optional[str] = None) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("🔄 ادامه", callback_data=f"ai_continue:{answer_id or 0}"),
            InlineKeyboardButton("🗑️", callback_data="group_dismiss"),
        ],
    ]
    return InlineKeyboardMarkup(rows)


def settings_keyboard(chat_id: int, settings: dict) -> InlineKeyboardMarkup:
    ai_on = bool(settings.get("ai_enabled", 1))
    short_on = bool(settings.get("short_replies", 1))
    mention_on = bool(settings.get("mention_only", 0))
    admin_on = bool(settings.get("admin_only", 0))
    fast_on = bool(settings.get("fast_path", 1))
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ AI فعال" if ai_on else "❌ AI خاموش", callback_data=f"gset:ai_enabled:{chat_id}")],
        [InlineKeyboardButton("✅ پاسخ کوتاه" if short_on else "📝 پاسخ کامل", callback_data=f"gset:short_replies:{chat_id}")],
        [InlineKeyboardButton("⚡ Fast-path روشن" if fast_on else "⚡ Fast-path خاموش", callback_data=f"gset:fast_path:{chat_id}")],
        [InlineKeyboardButton("📌 فقط منشن" if mention_on else "🧠 هوشمند (بدون منشن)", callback_data=f"gset:mention_only:{chat_id}")],
        [InlineKeyboardButton("👮 فقط ادمین" if admin_on else "👥 همه اعضا", callback_data=f"gset:admin_only:{chat_id}")],
        [InlineKeyboardButton("بستن", callback_data="group_dismiss")],
    ])


async def user_is_group_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """بررسی ادمین بودن کاربر در گروه (یا ادمین سراسری ربات)."""
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat:
        return False
    if user.id in getattr(config, "ADMIN_IDS", []):
        return True
    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
        status = member.status
        return status in (
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
            "administrator",
            "creator",
        )
    except Exception as exc:
        logger.debug("user_is_group_admin: %s", exc)
        return False


GROUP_WELCOME_TEXT = """✨ <b>سلام! من روز زیبا هستم</b>

در این گروه می‌تونم کمکتون کنم:

🧠 <b>هوش مصنوعی</b>
• منشن: <code>@{bot_username} سؤالتون</code>
• ریپلای به پیام من
• دستور: <code>/ask سؤالتون</code> یا <code>/ai سؤالتون</code>
• پیشوند: <code>! سؤالتون</code>

📊 بازار · 🌤️ آب‌وهوا · 📅 تقویم · 📥 دانلود

⚙️ ادمین‌ها: <code>/groupsettings</code> برای تنظیمات گروه
━━━━━━━━━━━━━━
💡 برای تجربه کامل‌تر، بهم تو پیوی پیام بده."""


async def send_group_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    if not chat or not is_group_chat(chat):
        return
    uname = get_bot_username(context) or "bot"
    text = GROUP_WELCOME_TEXT.format(bot_username=uname)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📖 راهنما", callback_data="group_help")],
        [InlineKeyboardButton("⚙️ تنظیمات گروه", callback_data="group_settings_open")],
        [InlineKeyboardButton("💬 شروع در پیوی", url=f"https://t.me/{uname}?start=group")],
    ])
    try:
        await context.bot.send_message(
            chat_id=chat.id,
            text=text,
            parse_mode="HTML",
            reply_markup=kb,
            disable_web_page_preview=True,
        )
    except Exception as exc:
        logger.warning("group welcome failed: %s", exc)


async def handle_my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    result = update.my_chat_member
    if not result:
        return
    chat = result.chat
    if not is_group_chat(chat):
        return
    old = result.old_chat_member.status if result.old_chat_member else ""
    new = result.new_chat_member.status if result.new_chat_member else ""
    if new in ("member", "administrator") and old in ("left", "kicked", ""):
        logger.info("Bot added to group %s (%s)", chat.id, chat.title)
        try:
            from bot.handlers.group_settings import ensure_group_settings_table
            ensure_group_settings_table()
        except Exception:
            pass
        await send_group_welcome(update, context)
