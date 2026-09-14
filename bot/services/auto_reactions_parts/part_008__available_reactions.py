from typing import Optional

# Auto-split part 8: _available_reactions
async def _available_reactions(token: str, chat_id: int | str) -> Optional[set[str]]:
    try:
        cid = int(chat_id)
    except (TypeError, ValueError):
        return None
    now = time.monotonic()
    cached = _available_cache.get(cid)
    ttl = float(getattr(config, "AUTO_REACTIONS_CHAT_CACHE_TTL", 900.0))
    if cached and now - cached[0] < ttl:
        return cached[1]
    ok, payload = await _api(token, "getChat", {"chat_id": chat_id})
    if not ok:
        return None
    raw = (payload.get("result") or {}).get("available_reactions")
    if raw is None:
        allowed = None
    else:
        allowed = {str(item.get("emoji")) for item in raw if isinstance(item, dict) and item.get("type") == "emoji" and item.get("emoji")}
    _available_cache[cid] = (now, allowed)
    return allowed
