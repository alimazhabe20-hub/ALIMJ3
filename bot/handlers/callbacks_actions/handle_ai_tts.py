"""Callback action: ai_tts.

Extracted from the legacy callback router while preserving its public behavior.
"""
from importlib import import_module

_CORE = import_module("bot.handlers.callbacks_core")

async def handle(update, context):
    # The old callback implementation exposes many helpers as module globals.
    # Mirror those globals here so the extracted action remains behavior-compatible.
    globals().update({k: v for k, v in vars(_CORE).items() if k != "button_handler"})
    query = update.callback_query
    data = query.data
    user_id = update.effective_user.id
    if data.startswith("ai_tts:"):
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
