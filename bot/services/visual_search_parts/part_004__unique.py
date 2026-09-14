from typing import Iterable

# Auto-split part 4: _unique
def _unique(items: Iterable[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        item = _normalize(item)
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out
