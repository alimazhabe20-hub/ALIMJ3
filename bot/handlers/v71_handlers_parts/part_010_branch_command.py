from telegram import Update
from telegram.ext import ContextTypes

# Auto-split part 10: branch_command
async def branch_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args=" ".join(context.args or []).strip(); uid=update.effective_user.id
    if not args:
        rows=list_branches(uid); await update.message.reply_text("🌿 شاخه‌ها:\n"+("\n".join("• "+x for x in rows) if rows else "خالی است.")); return
    if "=" not in args:
        await update.message.reply_text("🌿 فرمت: /branch نام=زمینه")
        return
    name,data=args.split("=",1); save_branch(uid,name.strip(),data.strip()); await update.message.reply_text("✅ شاخه ذخیره شد.")
