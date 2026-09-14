# Auto-split part 14: get_ai_result_keyboard
def get_ai_result_keyboard(user_id: int, answer_id: str = "", *, offer_continue: bool = False):
    """
    کیبورد زیر جواب AI.
    اگر offer_continue=True یا پاسخ بلند باشد، دکمه «ادامه پاسخ» اضافه می‌شود.
    """
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    rows = []
    aid = answer_id or get_last_answer_id(user_id) or ""
    last = get_last_answer(user_id) or ""
    should_continue = offer_continue or (len(last) >= 1800)
    if should_continue and aid:
        rows.append([
            InlineKeyboardButton("▶️ ادامه پاسخ", callback_data=f"ai_continue:{aid}")
        ])
    # مدل و حافظه از get_ai_keyboard جدا هستند؛ اینجا فقط ادامه
    if not rows:
        return None
    return InlineKeyboardMarkup(rows)
