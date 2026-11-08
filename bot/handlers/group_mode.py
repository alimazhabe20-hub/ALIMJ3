"""
Group Mode — پشتیبانی حرفه‌ای ربات در گروه‌ها و سوپرگروه‌ها.

قوانین UX گروه:
- فقط با منشن، ریپلای به ربات، یا دستورات صریح پاسخ می‌دهد (جلوگیری از اسپم).
- ReplyKeyboard استفاده نمی‌شود؛ فقط InlineKeyboard.
- پاسخ‌ها کوتاه‌تر، تمیزتر و با attribution (نام کاربر) هستند.
- استریم نوشتن لحظه‌ای فعال است.
"""
from __future__ import annotations

import re
from typing import Optional, Tuple

from telegram import Update, Chat, Message, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatType, ChatAction
from telegram.ext import ContextTypes

from bot.logger import logger
from bot.config import config


# --- Helpers ---------------------------------------------------------------

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
    uname = getattr(bot, "username", None) or ""
    return (uname or "").lstrip("@").lower()


def is_bot_mentioned(text: str, bot_username: str) -> bool:
    if not text or not bot_username:
        return False
    # @username anywhere (case-insensitive)
    pattern = rf"(?<!\w)@{re.escape(bot_username)}(?!\w)"
    return bool(re.search(pattern, text, flags=re.IGNORECASE))


def is_reply_to_bot(message: Optional[Message], bot_id: int) -> bool:
    if not message or not message.reply_to_message:
        return False
    replied = message.reply_to_message
    if replied.from_user and replied.from_user.id == bot_id:
        return True
    return False


def should_respond_in_group(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    allow_commands: bool = True,
) -> Tuple[bool, str]:
    """
    تصمیم می‌گیرد آیا ربات باید در گروه به این پیام پاسخ دهد یا نه.

    Returns:
        (should_respond, reason)
    """
    message = update.effective_message
    chat = update.effective_chat
    if not message or not chat or not is_group_chat(chat):
        return True, "private_or_unknown"

    text = (message.text or message.caption or "").strip()
    bot_id = context.bot.id
    bot_uname = get_bot_username(context)

    # 1) دستورات (شروع با /)
    if allow_commands and text.startswith("/"):
        return True, "command"

    # 2) منشن ربات
    if is_bot_mentioned(text, bot_uname):
        return True, "mention"

    # 3) ریپلای به پیام ربات
    if is_reply_to_bot(message, bot_id):
        return True, "reply"

    # 4) پیشوند اختیاری (قابل تنظیم)
    prefixes = getattr(config, "GROUP_TRIGGER_PREFIXES", ["!", "ربات", "هوشمند"])
    low = text.lower()
    for p in prefixes:
        p = (p or "").strip()
        if not p:
            continue
        if low.startswith(p.lower() + " ") or low == p.lower():
            return True, f"prefix:{p}"

    return False, "ignored"


def clean_group_prompt(text: str, bot_username: str) -> str:
    """منشن و پیشوند را از متن سؤال پاک می‌کند تا به AI تمیز برسد."""
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
    # حذف پیشوندهای رایج
    cleaned = re.sub(r"^(?:!|ربات|هوشمند)\s*", "", cleaned.strip(), flags=re.IGNORECASE)
    return cleaned.strip()


def group_attribution(user) -> str:
    """نام کاربر برای نمایش در پاسخ گروهی."""
    if not user:
        return "کاربر"
    name = (user.full_name or user.first_name or "کاربر").strip()
    if len(name) > 28:
        name = name[:25] + "…"
    return name


def group_ai_header(user, *, streaming: bool = False) -> str:
    name = group_attribution(user)
    if streaming:
        return f"🤖 <b>روز زیبا</b> · پاسخ به <b>{_esc(name)}</b>\n━━━━━━━━━━━━━━\n"
    return f"🤖 <b>روز زیبا</b> · برای <b>{_esc(name)}</b>\n━━━━━━━━━━━━━━\n"


def group_ai_footer() -> str:
    return "\n━━━━━━━━━━━━━━\n💡 ریپلای کن یا منشن کن تا ادامه بدیم"


def _esc(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def group_inline_actions(user_id: int, answer_id: Optional[str] = None) -> InlineKeyboardMarkup:
    """دکمه‌های مینیمال و حرفه‌ای مخصوص گروه."""
    rows = [
        [
            InlineKeyboardButton("🔄 ادامه", callback_data=f"ai_continue:{answer_id or 0}"),
            InlineKeyboardButton("🗑️ پاک کردن", callback_data="group_dismiss"),
        ],
        [
            InlineKeyboardButton("💬 چت خصوصی", url=f"https://t.me/{getattr(config, 'BOT_USERNAME', 'roozeziba_bot')}"),
        ],
    ]
    return InlineKeyboardMarkup(rows)


# متن خوش‌آمدگویی وقتی ربات به گروه اضافه می‌شود
GROUP_WELCOME_TEXT = """✨ <b>سلام! من روز زیبا هستم</b>

در این گروه می‌تونم کمکتون کنم:

🧠 <b>هوش مصنوعی</b>
• منشن کنید: <code>@{bot_username} سؤالتون</code>
• یا به پیام من ریپلای کنید
• یا بنویسید: <code>! سؤالتون</code>

📊 بازار · 🌤️ آب‌وهوا · 📅 تقویم · 📥 دانلود
و خیلی قابلیت‌های دیگه با دستورات `/help`

━━━━━━━━━━━━━━
💡 برای تجربه کامل‌تر، بهم تو پیوی پیام بده."""


async def send_group_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """وقتی ربات به گروه اضافه می‌شود."""
    chat = update.effective_chat
    if not chat or not is_group_chat(chat):
        return
    uname = get_bot_username(context) or "bot"
    text = GROUP_WELCOME_TEXT.format(bot_username=uname)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📖 راهنما", callback_data="group_help")],
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
    """تشخیص اضافه شدن ربات به گروه."""
    result = update.my_chat_member
    if not result:
        return
    chat = result.chat
    if not is_group_chat(chat):
        return
    old = result.old_chat_member.status if result.old_chat_member else ""
    new = result.new_chat_member.status if result.new_chat_member else ""
    # اضافه شدن یا ارتقا به عضو/ادمین
    if new in ("member", "administrator") and old in ("left", "kicked", ""):
        logger.info("Bot added to group %s (%s)", chat.id, chat.title)
        await send_group_welcome(update, context)
