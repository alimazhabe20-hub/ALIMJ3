from telegram import Update
from telegram.ext import ContextTypes

# Auto-split part 9: workspace_command
async def workspace_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args=" ".join(context.args or []).strip()
    if not args or "=" not in args:
        await update.message.reply_text("📁 فرمت: /workspace نام=داده")
        return
    name,data=args.split("=",1); set_workspace(update.effective_user.id,name.strip(),data.strip()); await update.message.reply_text("✅ Workspace ذخیره شد.")
