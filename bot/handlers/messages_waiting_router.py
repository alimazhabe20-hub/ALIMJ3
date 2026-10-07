"""Semantic message-routing handlers. Extracted from the legacy text handler without removing behavior."""
from .messages_common import *  # noqa: F401,F403
from . import messages_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})

async def handle_pre_ai_waiting(update, context, text, user_id, city=None, first_name=None):
    waiting = context.user_data.get("waiting_for")
    # ساخت یادآوری جدید از منوی «مدیریت یادآوری‌ها» باید قبل از AI عمومی هندل شود.
    # این مسیر باعث می‌شود جمله‌هایی مثل «فردا ساعت ۱۲ ظهر خبرم کن درس بخونم»
    # مستقیم ثبت شوند و به AI سپرده نشوند.
    if waiting == "reminder_new":
        if text.strip().lower() in ("لغو", "انصراف", "cancel"):
            context.user_data.pop("waiting_for", None)
            await _h_reminder_manager(update, context, user_id)
            return
        rem = parse_natural_reminder(text)
        if rem:
            body, when, repeat_type, repeat_every = rem
            add_reminder(user_id, body, when.isoformat(), repeat_type=repeat_type, repeat_every=repeat_every)
            context.user_data.pop("waiting_for", None)
            repeat_label = {
                "daily": "روزانه", "weekly": "هفتگی", "monthly": "ماهانه",
                "every_minutes": f"هر {repeat_every} دقیقه",
                "every_hours": f"هر {repeat_every} ساعت",
            }.get(repeat_type, "یک‌بار")
            await update.message.reply_text(
                f"⏰ یادآوری ثبت شد.\nموضوع: {body}\nزمان: {when.strftime('%Y-%m-%d %H:%M')}\nتکرار: {repeat_label}"
            )
            return
        await update.message.reply_text(
            "⚠️ زمان یادآوری را متوجه نشدم.\nمثلاً: «فردا ساعت ۱۲ ظهر خبرم کن درس بخونم» یا «فردا ساعت ۹ جلسه دارم»."
        )
        return
    if await _h_reminder_input(update, context, user_id, text):
        return
    return False
