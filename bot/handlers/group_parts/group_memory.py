"""حافظه کوتاه مکالمه در هر گروه (آخرین چند نوبت)."""
from __future__ import annotations

from collections import defaultdict, deque
from typing import Deque, List, Tuple

_HISTORY: dict[int, Deque[Tuple[str, str]]] = defaultdict(lambda: deque(maxlen=4))


def add_turn(chat_id: int, role: str, text: str) -> None:
    if not text:
        return
    _HISTORY[int(chat_id)].append((role, text[:500]))


def get_context(chat_id: int) -> str:
    items = list(_HISTORY.get(int(chat_id), []))
    if not items:
        return ""
    lines = []
    for role, text in items[-4:]:
        tag = "کاربر" if role == "user" else "ربات"
        lines.append(f"{tag}: {text}")
    return "\n".join(lines)


def clear_chat(chat_id: int) -> None:
    _HISTORY.pop(int(chat_id), None)
