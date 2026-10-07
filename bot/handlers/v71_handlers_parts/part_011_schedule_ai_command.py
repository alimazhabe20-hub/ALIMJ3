from telegram import Update
from telegram.ext import ContextTypes

# Auto-split part 11: schedule_ai_command
async def schedule_ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args=" ".join(context.args or []).strip()
    m=re.match(r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})(?:\s+(\d+))?\s+(.+)$",args)
    if not m:
        await update.message.reply_text("⏰ فرمت: /scheduleai 2026-09-14 09:00 60 متن وظیفه\nعدد 60 یعنی تکرار هر 60 دقیقه؛ حذفش کنید برای یک‌بار.")
        return
    run_at,repeat,prompt=m.groups(); jid=schedule_ai(update.effective_user.id,prompt,run_at,int(repeat or 0)); await update.message.reply_text(f"✅ وظیفه AI ثبت شد. شناسه: {jid}")
