from telegram import Update
from telegram.ext import ContextTypes

# Auto-split part 8: v71_selftest_command
async def v71_selftest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result=self_test(); await update.message.reply_text("🧪 Self-Test\n"+str(result))
