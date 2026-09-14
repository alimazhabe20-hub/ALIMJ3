async def _send_ai_answer(update, user_id, answer: str, *, prompt: str = "", stream: bool = True):
    """ارسال جواب AI کامل — بدون کلید مدل/حافظه؛ فقط در صورت نیاز دکمه ادامه."""
    msg = update.message
    aid = store_answer(user_id, answer, prompt=prompt)
    offer = _looks_truncated(answer) or len(answer or "") >= 1800
    # فقط دکمه ادامه؛ کلیدهای «انتخاب مدل» و «حذف حافظه» زیر پاسخ نباشد.
    kb = get_ai_result_keyboard(user_id, aid, offer_continue=offer)
    return await _reply_long_text(msg, answer, prefix="🤖 ", reply_markup=kb)
