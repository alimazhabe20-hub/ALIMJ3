# Auto-split part 9: _set_reaction
async def _set_reaction(token: str, chat_id: int | str, message_id: int, emoji: str) -> bool:
    reaction_json = json.dumps([{"type": "emoji", "emoji": emoji}], ensure_ascii=False)
    ok, payload = await _api(token, "setMessageReaction", {
        "chat_id": chat_id,
        "message_id": message_id,
        "reaction": reaction_json,
        "is_big": "true" if bool(getattr(config, "AUTO_REACTIONS_BIG", False)) else "false",
    })
    if ok:
        return True

    description = str(payload.get("description", "unknown Telegram error"))
    # Only pay the extra getChat request when Telegram actually rejects the emoji.
    if "REACTION_INVALID" in description or "reaction" in description.lower():
        try:
            _available_cache.pop(int(chat_id), None)
        except (TypeError, ValueError):
            pass
        allowed = await _available_reactions(token, chat_id)
        if allowed is not None:
            candidate = emoji if emoji in allowed else next(
                (x for x in ("❤️", "👍", "🔥", "👏", "😂") if x in allowed), None
            )
            if candidate:
                ok2, payload2 = await _api(token, "setMessageReaction", {
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "reaction": json.dumps([{"type": "emoji", "emoji": candidate}], ensure_ascii=False),
                    "is_big": "false",
                })
                if ok2:
                    return True
                description = str(payload2.get("description", description))
    logger.warning("auto reaction failed chat=%s message=%s emoji=%s: %s", chat_id, message_id, emoji, description[:300])
    return False
