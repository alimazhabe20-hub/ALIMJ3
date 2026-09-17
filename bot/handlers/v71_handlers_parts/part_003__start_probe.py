# Auto-split part 3: _start_probe
async def _start_probe(update, context, url: str):
    url = extract_url(url) or ""
    if not url:
        await update.message.reply_text(ux_text(_dl_lang(update), "invalid"))
        return
    from bot.services.v72_platform import ux_text
    lang = _dl_lang(update)
    notice = await update.message.reply_text(ux_text(lang, "checking"))
    try:
        info = await probe(url)
        if info.get("error") == "youtube_disabled" or (not info.get("supported") and info.get("error") == "youtube_disabled"):
            from bot.services.downloader import user_message
            try:
                await notice.edit_text(user_message("youtube_disabled"))
            except Exception:
                await update.message.reply_text(user_message("youtube_disabled"))
            return
        token = secrets.token_urlsafe(9)
        context.user_data[f"dl:{token}"] = {"url": url, "info": info}
        title = str(info.get("title") or "فایل")[:100]
        labels = {
            "fa": {"best":"🎬 بهترین کیفیت","1080p":"📺 تا 1080p","720p":"📺 تا 720p","480p":"📺 تا 480p","audio":"🎵 فقط صدا (MP3)","direct":"📦 دریافت مستقیم","cancel":"❌ لغو"},
            "en": {"best":"🎬 Best quality","1080p":"📺 Up to 1080p","720p":"📺 Up to 720p","480p":"📺 Up to 480p","audio":"🎵 Audio only (MP3)","direct":"📦 Direct download","cancel":"❌ Cancel"},
            "ar": {"best":"🎬 أفضل جودة","1080p":"📺 حتى 1080p","720p":"📺 حتى 720p","480p":"📺 حتى 480p","audio":"🎵 صوت فقط (MP3)","direct":"📦 تنزيل مباشر","cancel":"❌ إلغاء"},
        }[lang]
        rows = [
            [InlineKeyboardButton(labels["best"], callback_data=f"dl:q:{token}:best"), InlineKeyboardButton(labels["1080p"], callback_data=f"dl:q:{token}:1080p")],
            [InlineKeyboardButton(labels["720p"], callback_data=f"dl:q:{token}:720p"), InlineKeyboardButton(labels["480p"], callback_data=f"dl:q:{token}:480p")],
            [InlineKeyboardButton(labels["audio"], callback_data=f"dl:q:{token}:audio")],
            [InlineKeyboardButton(labels["cancel"], callback_data=f"dl:cancel:{token}")],
        ]
        if not info.get("supported"):
            rows = [[InlineKeyboardButton(labels["direct"], callback_data=f"dl:q:{token}:best")],[InlineKeyboardButton(labels["cancel"], callback_data=f"dl:cancel:{token}")]]
        await notice.edit_text(f"{ux_text(lang, 'prepared')}\n\n📄 {title}\n\n{ux_text(lang, 'choose')}", reply_markup=InlineKeyboardMarkup(rows))
    except Exception:
        logger.exception("downloader probe failed")
        await notice.edit_text(ux_text(lang, "probe_failed"))
    finally:
        context.user_data.pop("waiting_for", None)
