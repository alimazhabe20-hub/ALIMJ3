async def _keep_typing(bot, chat_id, stop_event):
    """تا وقتی پاسخ آماده نشده، مدام حالت «در حال نوشتن...» را نشان بده."""
    import asyncio
    from telegram.constants import ChatAction
    while not stop_event.is_set():
        try:
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        except Exception as _exc:
            logger.debug("%s: %s", __name__, _exc)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=4)
        except Exception as _exc:
            logger.debug("%s: %s", __name__, _exc)
