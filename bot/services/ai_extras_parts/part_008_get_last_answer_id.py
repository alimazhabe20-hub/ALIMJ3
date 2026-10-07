from typing import Optional

# Auto-split part 8: get_last_answer_id
def get_last_answer_id(user_id: int) -> Optional[str]:
    return _LAST_ANSWER_ID.get(user_id)
