"""
Group Mode — پشتیبانی حرفه‌ای ربات در گروه‌ها و سوپرگروه‌ها.

قوانین UX گروه:
- فقط با منشن، ریپلای به ربات، دستورات صریح یا پیشوند پاسخ می‌دهد.
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


def should_respond_in_group(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    allow_commands: bool = True,
) -> Tuple[bool, str]:
    message = update.effective_message
    chat = update.effective_chat
    if not message or not chat or not is_group_chat(chat):
        return True, "private_or_unknown"

    text = (message.text or message.caption or "").strip()
    bot_id = context.bot.id
    bot_uname = get_bot_username(context)

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
    ai_label = "✅ AI فعال" if ai_on else "❌ AI خاموش"
    short_label = "✅ پاسخ کوتاه" if short_on else "📝 پاسخ کامل"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(ai_label, callback_data=f"gset:ai:{chat_id}")],
        [InlineKeyboardButton(short_label, callback_data=f"gset:short:{chat_id}")],
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
