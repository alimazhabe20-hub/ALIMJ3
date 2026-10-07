from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from bot.services.auto_reactions import httpx

# Auto-split part 6: _get_client
async def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=httpx.Timeout(
            float(getattr(config, "AUTO_REACTIONS_TIMEOUT", 3.0)),
            connect=2.0,
        ), limits=httpx.Limits(max_connections=4, max_keepalive_connections=2))
    return _client
