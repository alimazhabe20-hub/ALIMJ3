def _apply_voice_chat_flags(context, text: str) -> str | None:
    """
    فعال/غیرفعال کردن حالت مکالمه ویسی.
    پیام تأیید برای کاربر برمی‌گرداند یا None.
    """
    if wants_end_voice_chat(text):
        context.user_data["ai_voice_chat"] = False
        return "📝 حالت ویس خاموش شد. از این به بعد جواب‌ها بیشتر متنی است."
    if wants_voice_chat_mode(text):
        context.user_data["ai_voice_chat"] = True
        return (
            "🎙️ حالت مکالمه ویسی روشن شد.\n"
            "هر چی بگی (متن یا ویس) سعی می‌کنم با صدا جواب بدم.\n"
            "برای خاموش کردن بگو: «قطع ویس» یا «فقط متن»."
        )
    return None
