async def _send_ai_answer(update, user_id, answer: str, *, prompt: str = "", stream: bool = True):
    """ارسال جواب AI کامل — بدون کلید مدل/حافظه؛ فقط در صورت نیاز دکمه ادامه."""
    msg = update.message
    # اگر Provider وسط جمله قطع کرده، قبل از ارسال پاسخ یک بار ادامهٔ خودکار بگیر.
    # این کار مشکل «پاسخ ناقص» را به کاربر منتقل نمی‌کند و فقط یک continuation امن دارد.
    if _looks_truncated(answer):
        try:
            from bot.services.ai_service import ask_ai
            continuation_prompt = (
                "پاسخ قبلی در میانه قطع شده است. فقط از همان نقطه ادامه بده؛ "
                "متن قبلی را تکرار نکن، مقدمه نده و پاسخ را با یک جمله کامل تمام کن."
            )
            extra, _provider = await ask_ai(user_id, continuation_prompt)
            extra = (extra or "").strip()
            if extra:
                answer = answer.rstrip() + " " + extra
        except Exception as _exc:
            logger.warning("AI auto-continuation failed: %s", _exc)

    aid = store_answer(user_id, answer, prompt=prompt)
    offer = _looks_truncated(answer) or len(answer or "") >= 1800
    # فقط دکمه ادامه؛ کلیدهای «انتخاب مدل» و «حذف حافظه» زیر پاسخ نباشد.
    kb = get_ai_result_keyboard(user_id, aid, offer_continue=offer)
    return await _reply_long_text(msg, answer, prefix="🤖 ", reply_markup=kb)
