from typing import Any
from typing import Callable

# Auto-split part 58: subscribe
def subscribe(event: str, callback: Callable[[dict[str,Any]],Any]) -> None:
    if callable(callback) and len(_EVENTS[str(event)])<32:_EVENTS[str(event)].append(callback)
