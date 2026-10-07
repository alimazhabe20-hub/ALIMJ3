"""Compatibility: get_ai_answer_keyboard for unified messages.py."""

def get_ai_answer_keyboard(user_id=None):
    """کیبورد زیر پاسخ AI.

    اول get_ai_result_keyboard (ادامه پاسخ + اکشن هوشمند) را امتحان می‌کند؛
    اگر در دسترس نبود به get_ai_keyboard برمی‌گردد.
    """
    try:
        from bot.services.ai_extras import get_ai_result_keyboard
        return get_ai_result_keyboard(user_id)
    except Exception:
        from bot.utils.keyboard_factory import get_ai_keyboard
        return get_ai_keyboard(user_id)
