from typing import Optional

# Auto-split part 6: get_last_answer
def get_last_answer(user_id: int) -> Optional[str]:
    """آخرین جواب AI همین کاربر."""
    return _LAST_ANSWER.get(user_id) or None
