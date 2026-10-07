from typing import Any

# Auto-split part 28: emit
async def emit(event: str, payload: dict[str,Any]) -> int:
    count=0
    for cb in list(_EVENTS.get(str(event),[])):
        try:
            r=cb(payload); await r if asyncio.iscoroutine(r) else None; count+=1
        except Exception: pass
    return count
