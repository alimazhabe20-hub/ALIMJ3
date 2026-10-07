from telegram import Update
from telegram.ext import ContextTypes

# Auto-split part 2: downloader_entry_v71
async def downloader_entry_v71(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = " ".join(context.args or []).strip() if getattr(context, "args", None) else ""
    url = extract_url(args) if args else None
    if url:
        await _start_probe(update, context, url)
        return
    context.user_data["waiting_for"] = "downloader_url_v71"
    from bot.services.v72_platform import ux_text
    lang = _dl_lang(update)
    await update.message.reply_text(ux_text(lang, "download_title") + "\n\n" + ux_text(lang, "intro"))
