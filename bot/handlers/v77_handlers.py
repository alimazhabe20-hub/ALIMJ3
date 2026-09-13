from __future__ import annotations
import json
from telegram import Update
from telegram.ext import ContextTypes

async def v77_test_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        from bot.config import config
        if config.ADMIN_IDS and update.effective_user and update.effective_user.id not in config.ADMIN_IDS:
            await update.effective_message.reply_text("⛔ دسترسی مجاز نیست."); return
        from bot.services.v77_platform import self_test
        r=self_test("."); lines=["🚀 ALIMJ3 V77 Ultimate",f"وضعیت: {'✅ سالم' if r.get('ok') else '⚠️ نیازمند بررسی'}"]
        lines += [f"{'✅' if v else '❌'} {k}" for k,v in r.get('checks',{}).items()]
        await update.effective_message.reply_text("\n".join(lines))
    except Exception:
        await update.effective_message.reply_text("⚠️ تست V77 موقتاً در دسترس نیست.")

async def v77_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        from bot.config import config
        if config.ADMIN_IDS and update.effective_user and update.effective_user.id not in config.ADMIN_IDS:
            await update.effective_message.reply_text("⛔ دسترسی مجاز نیست."); return
        from bot.services.v77_platform import system_snapshot
        await update.effective_message.reply_text("🧠 V77 Ultimate Status\n\n"+json.dumps(system_snapshot("."),ensure_ascii=False,indent=2)[:12000])
    except Exception:
        await update.effective_message.reply_text("⚠️ وضعیت V77 موقتاً در دسترس نیست.")
