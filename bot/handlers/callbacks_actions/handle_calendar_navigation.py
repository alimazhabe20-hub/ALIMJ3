"""Callback action: calendar_navigation.

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
    if data.startswith("cal_"):
        await _safe_answer(query)
        parts = data.split("_")
        year, month, day = int(parts[1]), int(parts[2]), int(parts[3])
        if month < 1:
            month = 12
            year -= 1
        elif month > 12:
            month = 1
            year += 1
        text = get_calendar_text(year, month, day, user_id)
        await query.edit_message_text(
            text,
            reply_markup=get_calendar_buttons(year, month, day, user_id)
        )
        return
