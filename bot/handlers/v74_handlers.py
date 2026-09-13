"""V74 operator-safe diagnostics command."""
from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes


async def v74_test_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        from bot.config import config
        if update.effective_user and config.ADMIN_IDS and update.effective_user.id not in config.ADMIN_IDS:
            await update.effective_message.reply_text("⛔ دسترسی مجاز نیست.")
            return
        from bot.services.v74_platform import self_test
        result = self_test(".")
        checks = result.get("checks", {})
        lines = ["🛡 V74 Reliability & Intelligence Core", f"وضعیت: {'✅ سالم' if result.get('ok') else '⚠️ نیازمند بررسی'}"]
        lines.extend(f"{'✅' if v else '❌'} {k}" for k, v in checks.items())
        await update.effective_message.reply_text("\n".join(lines))
    except Exception:
        await update.effective_message.reply_text("⚠️ تست V74 موقتاً در دسترس نیست.")
