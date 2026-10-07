from typing import Optional

# Auto-split part 15: build_continue_prompt
def build_continue_prompt(user_id: int, answer_id: str = "") -> Optional[str]:
    """ساخت پرامپت ادامه برای AI بدون تکرار بخش قبلی."""
    prev = None
    prompt = None
    if answer_id:
        prev = get_stored_answer(answer_id, user_id)
        prompt = get_stored_prompt(answer_id, user_id)
    if not prev:
        prev = get_last_answer(user_id)
    if not prompt:
        prompt = get_last_prompt(user_id)
    if not prev:
        return None
    tail = prev[-900:] if len(prev) > 900 else prev
    base = (
        "ادامه بده دقیقاً از جایی که پاسخ قبلی قطع شد. "
        "هیچ بخشی از متن قبلی را تکرار نکن. مستقیم ادامه بده.\n\n"
        f"--- انتهای پاسخ قبلی ---\n{tail}\n--- ادامه از اینجا ---"
    )
    if prompt:
        return f"موضوع اصلی کاربر: {prompt}\n\n{base}"
    return base
