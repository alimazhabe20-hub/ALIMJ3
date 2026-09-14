async def _send_ai_voice(update_or_msg, text: str, user_id: int, reply_markup=None):
    """ارسال ویس با پیام وضعیت «در حال ویس دادن»."""
    msg = getattr(update_or_msg, "message", None) or update_or_msg
    notice = await msg.reply_text("🔊 در حال ویس دادن...")
    try:
        audio = await text_to_speech(text)
        from io import BytesIO
        bio = BytesIO(audio)
        bio.name = "reply.mp3"
        kwargs = {"audio": bio, "caption": "🔊"}
        if reply_markup is not None:
            kwargs["reply_markup"] = reply_markup
        await msg.reply_audio(**kwargs)
    finally:
        try:
            await notice.delete()
        except Exception as _exc:
            logger.debug("%s: %s", __name__, _exc)
