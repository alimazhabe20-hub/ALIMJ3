async def _handle_ai_tts(query, update, context, data, user_id):
    """Extracted callback branch; preserves original behavior."""
    from bot.services.ai_extras import get_stored_answer
    from bot.services.ai_service import text_to_speech
    from io import BytesIO
    aid = data.split(":", 1)[1]
    text = get_stored_answer(aid, user_id)
    if not text:
        await _safe_answer(query, "این جواب منقضی شده. دوباره بپرس.", show_alert=True)
        return
    await _safe_answer(query, "در حال ویس دادن...")
    try:
        notice = await query.message.reply_text("🔊 در حال ویس دادن...")
        audio = await text_to_speech(text)
        bio = BytesIO(audio)
        bio.name = "answer.mp3"
        await query.message.reply_audio(audio=bio, caption="🔊")
        try:
            await notice.delete()
        except Exception as _exc:
            logger.debug("%s: %s", __name__, _exc)
    except Exception as e:
        await query.message.reply_text(f"⚠️ ویس ساخته نشد: {e}")
    return
