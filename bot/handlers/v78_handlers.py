from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes


def _lang(update: Update) -> str:
    try:
        from bot.database import get_user
        row = get_user(update.effective_user.id) if update.effective_user else None
        value = (row.get("language") if isinstance(row, dict) else getattr(row, "language", None)) or "fa"
        return value if value in {"fa", "en", "ar"} else "fa"
    except Exception:
        return "fa"


async def update_center_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        from bot.services.update_center import check_for_updates, update_summary
        result = await __import__("asyncio").to_thread(check_for_updates, force=True)
        await update.effective_message.reply_text(update_summary(result, _lang(update)))
    except Exception:
        await update.effective_message.reply_text("⚠️ مرکز بروزرسانی موقتاً در دسترس نیست.")
