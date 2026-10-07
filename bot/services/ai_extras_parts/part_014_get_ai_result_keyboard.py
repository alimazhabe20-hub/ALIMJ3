# Auto-split part 14: get_ai_result_keyboard

def get_ai_result_keyboard(user_id: int, answer_id: str = "", *, offer_continue: bool = False):
    """Context-aware inline actions under AI answers."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    from bot.services.telegram_enhancements import smart_action_keyboard

    rows = []
    aid = answer_id or get_last_answer_id(user_id) or ""
    last = get_last_answer(user_id) or ""
    should_continue = offer_continue or (len(last) >= 1800)
    if should_continue and aid:
        rows.append([InlineKeyboardButton("▶️ ادامه پاسخ", callback_data=f"ai_continue:{aid}")])
    smart = smart_action_keyboard(last, answer_id=aid)
    if smart:
        rows.extend(smart.inline_keyboard)
    return InlineKeyboardMarkup(rows) if rows else None
