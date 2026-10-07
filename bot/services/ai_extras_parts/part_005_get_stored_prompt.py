from typing import Optional

# Auto-split part 5: get_stored_prompt
def get_stored_prompt(answer_id: str, user_id: int) -> Optional[str]:
    item = _ANSWER_CACHE.get(answer_id)
    if not item:
        return None
    if len(item) == 4:
        uid, _text, exp, prompt = item
    else:
        uid, _text, exp = item
        prompt = ""
    if exp < time.time() or uid != user_id:
        return None
    return prompt or _LAST_PROMPT.get(user_id)
