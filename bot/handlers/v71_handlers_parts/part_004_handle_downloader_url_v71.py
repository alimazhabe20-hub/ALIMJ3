from telegram import Update
from telegram.ext import ContextTypes

# Auto-split part 4: handle_downloader_url_v71
async def handle_downloader_url_v71(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> bool:
    waiting = context.user_data.get("waiting_for")
    if waiting != "downloader_url_v71":
        return False
    url = extract_url(text)
    if not url:
        # Do not consume ReplyKeyboard buttons while waiting for a downloader URL.
        # Buttons such as "🔙 بازگشت" are routed by the normal menu handler;
        # they are not downloader input and must never trigger the invalid-URL message.
        stripped = (text or "").strip()
        if (
            "بازگشت" in stripped
            or stripped.startswith(("📥", "🔙", "🏠", "📊", "🥇", "🗓", "🧠", "⚙️", "🔔", "💾", "🌐", "📚", "🛠", "⬅️", "➡️"))
        ):
            context.user_data.pop("waiting_for", None)
            return False
        await update.message.reply_text(ux_text(_dl_lang(update), "invalid"))
        return True
    context.user_data.pop("waiting_for", None)

    # Instagram / social: same UX as insta-downloader-bot — download immediately
    try:
        from bot.services.insta_downloader import is_social_url
    except Exception:
        is_social_url = lambda _u: False  # type: ignore

    if is_social_url(text):
        await _download_social_direct(update, context, url)
        return True

    await _start_probe(update, context, url)
    return True
