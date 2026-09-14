from telegram import Update
from telegram.ext import ContextTypes

# Auto-split part 12: personalize_command
async def personalize_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args=" ".join(context.args or []).strip()
    if not args:
        await update.message.reply_text("⚙️ فرمت: /personalize fa|en|ar [short|balanced|long] [fast|balanced|quality]")
        return
    parts=args.split()
    lang=parts[0].lower() if parts else None
    style=parts[1].lower() if len(parts)>1 else None
    mode=parts[2].lower() if len(parts)>2 else None
    if lang not in SUPPORTED_LANGS:
        await update.message.reply_text("❌ زبان فقط fa / en / ar است."); return
    if style and style not in {"short","balanced","long"}:
        await update.message.reply_text("❌ سبک پاسخ: short / balanced / long"); return
    if mode and mode not in {"fast","balanced","quality"}:
        await update.message.reply_text("❌ حالت AI: fast / balanced / quality"); return
    current=personalize(update.effective_user.id,lang,style,mode,None)
    await update.message.reply_text(f"✅ شخصی‌سازی ذخیره شد.\n🌍 {current['language']}\n✍️ {current['response_style']}\n🤖 {current['ai_mode']}")
