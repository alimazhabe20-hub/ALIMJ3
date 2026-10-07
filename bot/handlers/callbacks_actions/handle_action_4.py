"""Callback action: action_4.

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
    if data == "ai_noop":
        await _safe_answer(query, "هیچ مدل فعالی تنظیم نشده است.", show_alert=True)
        return
