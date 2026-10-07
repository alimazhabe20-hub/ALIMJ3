# Auto-split part 12: enqueue_auto_reaction
def enqueue_auto_reaction(update) -> bool:
    """Fast, non-blocking hook used by the message handler.

    Classification and queueing are local-only; all Telegram I/O happens in a
    single background worker so the AI/message path never waits for reactions.
    """
    if not _enabled() or not update or not getattr(update, "message", None):
        return False
    message = update.message
    if not getattr(message, "text", None) or getattr(message, "from_user", None) is None:
        return False
    if getattr(message.from_user, "is_bot", False):
        return False
    chat = getattr(update, "effective_chat", None)
    if not chat or not _scope_allows(getattr(chat, "type", None)):
        return False
    result = classify_reaction(message.text)
    if result is None:
        return False
    category, emoji, confidence = result
    user_id = int(message.from_user.id)
    now = time.monotonic()
    cooldown = max(0.0, float(getattr(config, "AUTO_REACTIONS_COOLDOWN", 0.0)))
    if now - _last_by_user.get(user_id, 0.0) < cooldown:
        return False
    key = (int(chat.id), int(message.message_id))
    if not _mark_seen(key):
        return False
    if not (getattr(config, "BOT_TOKEN", "") or "").strip():
        return False
    _ensure_worker()
    try:
        _queue.put_nowait((chat.id, message.message_id, emoji, user_id, category, confidence))
    except asyncio.QueueFull:
        return False
    _last_by_user[user_id] = now
    return True
