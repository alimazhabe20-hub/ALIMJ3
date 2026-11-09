"""حافظه کوتاه و تمیز برای گروه — فقط ۲ نوبت آخر کاربر، بدون متن‌های بلند ربات."""
from __future__ import annotations

from collections import defaultdict, deque
from typing import Deque, Tuple

# فقط سؤال‌های اخیر کاربر (نه جواب‌های بلند ربات)
_USER_QS: dict[int, Deque[str]] = defaultdict(lambda: deque(maxlen=2))


def add_turn(chat_id: int, role: str, text: str) -> None:
    if not text:
        return
    t = " ".join(str(text).split())
    if role == "user":
        if len(t) > 200:
            t = t[:200] + "…"
        _USER_QS[int(chat_id)].append(t)
    # جواب ربات را ذخیره نکن تا پرامپت آلوده نشود


def get_context(chat_id: int) -> str:
    items = list(_USER_QS.get(int(chat_id), []))
    if not items:
        return ""
    # فقط اگر بیش از یک سؤال باشد زمینه بده
    if len(items) == 1:
        return ""
    prev = items[-2]
    return f"سؤال قبلی کاربر: {prev}"


def clear_chat(chat_id: int) -> None:
    _USER_QS.pop(int(chat_id), None)
