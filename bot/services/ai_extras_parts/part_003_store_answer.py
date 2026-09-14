# Auto-split part 3: store_answer
def store_answer(user_id: int, text: str, prompt: str = "") -> str:
    """ذخیره جواب برای دکمه ویس، ادامه پاسخ و درخواست «ویس بفرست»."""
    aid = hashlib.md5(f"{user_id}:{time.time()}:{text[:80]}".encode()).hexdigest()[:12]
    _ANSWER_CACHE[aid] = (user_id, text or "", time.time() + _CACHE_TTL, prompt or "")
    if text:
        _LAST_ANSWER[user_id] = text
        _LAST_ANSWER_ID[user_id] = aid
    if prompt:
        _LAST_PROMPT[user_id] = prompt
    if len(_ANSWER_CACHE) > 2000:
        now = time.time()
        dead = [k for k, v in _ANSWER_CACHE.items() if v[2] < now]
        for k in dead[:500]:
            _ANSWER_CACHE.pop(k, None)
    return aid
