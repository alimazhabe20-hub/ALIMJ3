"""Callback action: ai_exit.

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
    if data == "ai_exit":
        context.user_data.pop("ai_mode", None)
        context.user_data.pop("ai_shopping_mode", None)
        context.user_data.pop("waiting_for", None)
        await _safe_answer(query)
        await query.message.reply_text("➕ منوی بیشتر:", reply_markup=get_more_keyboard())
        return
