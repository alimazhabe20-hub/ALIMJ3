# Auto-split part 10: _worker
async def _worker() -> None:
    while True:
        item = await _queue.get()
        try:
            chat_id, message_id, emoji, user_id, category, confidence = item
            token = (getattr(config, "BOT_TOKEN", "") or "").strip()
            if token and await _set_reaction(token, chat_id, message_id, emoji):
                logger.info("auto reaction applied user=%s chat=%s message=%s category=%s emoji=%s confidence=%.2f", user_id, chat_id, message_id, category, emoji, confidence)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.debug("auto reaction worker error: %s", exc)
        finally:
            _queue.task_done()
