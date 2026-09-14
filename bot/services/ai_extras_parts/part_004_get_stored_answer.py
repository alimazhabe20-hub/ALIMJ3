from typing import Optional

# Auto-split part 4: get_stored_answer
def get_stored_answer(answer_id: str, user_id: int) -> Optional[str]:
    item = _ANSWER_CACHE.get(answer_id)
    if not item:
        return None
    uid, text, exp, _prompt = item if len(item) == 4 else (*item, "")
    if exp < time.time() or uid != user_id:
        return None
    return text
