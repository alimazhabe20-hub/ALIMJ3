from __future__ import annotations
import os
from telegram import Update
from telegram.ext import ContextTypes
from bot.logger import logger
from bot.services.v72_platform import qa_snapshot

async def v72_test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    result = qa_snapshot(root)
    ruff = result.get("ruff", {})
    ruff_line = "Ruff: OK" if ruff.get("available") and ruff.get("ok") else "Ruff: در این محیط نصب/فعال نیست" if not ruff.get("available") else "Ruff: خطا دارد"
    await update.message.reply_text(
        "🧪 V72 Quality Check\n\n"
        f"Compile: {'OK' if result.get('compile', {}).get('ok') else 'FAIL'}\n"
        f"{ruff_line}\n\n"
        "جزئیات فنی فقط در لاگ/محیط مدیریت نگه داشته می‌شود."
    )
