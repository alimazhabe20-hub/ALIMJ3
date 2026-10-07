from typing import Optional

# Auto-split part 7: get_last_prompt
def get_last_prompt(user_id: int) -> Optional[str]:
    return _LAST_PROMPT.get(user_id)
