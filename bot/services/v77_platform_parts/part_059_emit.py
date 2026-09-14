from typing import Any

# Auto-split part 59: emit
async def emit(event: str, payload: dict[str,Any]) -> int:
    count=0
    for cb in list(_EVENTS.get(str(event),[])):
        try:
            r=cb(payload)
            if asyncio.iscoroutine(r):await asyncio.wait_for(r,timeout=10)
            count+=1
        except Exception:pass
    return count
