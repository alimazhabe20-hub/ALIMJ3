"""Callback action: ai_model.

Extracted from the legacy callback router while preserving its public behavior.
"""
from importlib import import_module

_CORE = import_module("bot.handlers.callbacks_core")

async def handle(update, context):
    # The old callback implementation exposes many helpers as module globals.
    # Mirror those globals here so the extracted action remains behavior-compatible.
    globals().update({k: v for k, v in vars(_CORE).items() if k != "button_handler"})
    query = update.callback_query
    data = query.data
    user_id = update.effective_user.id
    if data.startswith("ai_provider:") or data.startswith("ai_model:"):
        # ai_provider: انتخاب ارائه‌دهنده (همه مدل‌هایش شامل می‌شود)
        # ai_model: سازگاری با پیام‌های قدیمی
        try:
            index = int(data.split(":", 1)[1])
            providers = available_providers()
            provider, label = providers[index]
        except (ValueError, IndexError):
            await _safe_answer(query, "❌ این سرویس دیگر در دسترس نیست.", show_alert=True)
            return
        set_selected_provider(user_id, provider)
        await _safe_answer(query, f"✅ فعال شد: {label}", show_alert=False)
        await query.edit_message_reply_markup(reply_markup=get_ai_keyboard(user_id))
        return
