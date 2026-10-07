async def _ask_ai_with_typing(update, context, user_id, text):
    """AI request with stable chunked output and safe fallback semantics."""
    import asyncio
    stop_event = asyncio.Event()
    chat_id = update.effective_chat.id
    # فقط _ask_ai_stream_and_send یک پیام «✍️ در حال نوشتن...» می‌فرستد.
    # اینجا فقط ChatAction.TYPING برای وضعیت تایپ تلگرام فعال می‌شود تا
    # پیام وضعیت دوبار روی صفحه ایجاد نشود.
    from bot.utils.task_manager import spawn
    task = spawn(_keep_typing(context.bot, chat_id, stop_event), name=f"typing-{chat_id}")
    try:
        try:
            if not AI_LIMITER.allow(user_id):
                await update.message.reply_text(platform_t(user_id, "limit"))
                return None
            enriched = text + build_ai_context(user_id, text)
            result = await HEAVY_QUEUE.run(lambda: _ask_ai_stream_and_send(update, context, user_id, enriched))
            context.user_data["_ai_already_sent"] = True
            return result
        except Exception as stream_error:
            logger.warning("AI chunked stream failed, using canonical fallback: %s", stream_error)
            context.user_data["_ai_already_sent"] = False
            enriched = text + build_ai_context(user_id, text)
            return await HEAVY_QUEUE.run(lambda: ask_ai(user_id, enriched))
    finally:
        stop_event.set()
        try:
            await task
        except Exception as _exc:
            logger.debug("%s: %s", __name__, _exc)
