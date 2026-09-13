from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes

async def v75_test_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        from bot.config import config
        if config.ADMIN_IDS and update.effective_user and update.effective_user.id not in config.ADMIN_IDS:
            await update.effective_message.reply_text("⛔ دسترسی مجاز نیست."); return
        from bot.services.v75_platform import self_test
        r=self_test("."); c=r.get("checks",{})
        lines=["🚀 V75 Intelligence & Automation Core",f"وضعیت: {'✅ سالم' if r.get('ok') else '⚠️ نیازمند بررسی'}"]
        lines += [f"{'✅' if v else '❌'} {k}" for k,v in c.items()]
        await update.effective_message.reply_text("\n".join(lines))
    except Exception:
        await update.effective_message.reply_text("⚠️ تست V75 موقتاً در دسترس نیست.")

async def v75_memory_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        from bot.services.v75_platform import recall
        rows=recall(update.effective_user.id,limit=10)
        if not rows: await update.effective_message.reply_text("🧠 حافظه V75 خالی است."); return
        await update.effective_message.reply_text("🧠 حافظه V75\n\n"+"\n".join(f"• {x['category']} / {x['key']}: {x['value']}" for x in rows))
    except Exception: await update.effective_message.reply_text("⚠️ حافظه موقتاً در دسترس نیست.")
