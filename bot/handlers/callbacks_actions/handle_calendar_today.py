"""Callback action: calendar_today.

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
    if data == "calendar_today":
        await _safe_answer(query)
        today = get_today_tehran()
        text = get_calendar_text(today.year, today.month, today.day, user_id)
        await query.edit_message_text(
            text,
            reply_markup=get_calendar_buttons(today.year, today.month, today.day, user_id)
        )
        return
