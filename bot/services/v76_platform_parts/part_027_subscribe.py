from typing import Any
from typing import Callable

# Auto-split part 27: subscribe
def subscribe(event: str, callback: Callable[[dict[str,Any]],Any]) -> None:
    if callable(callback): _EVENTS[str(event)][:20].append(callback)
