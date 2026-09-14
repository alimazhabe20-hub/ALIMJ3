async def _handle_ai_exit(query, update, context, data, user_id):
    """Extracted callback branch; preserves original behavior."""
    context.user_data.pop("ai_mode", None)
    context.user_data.pop("ai_shopping_mode", None)
    context.user_data.pop("waiting_for", None)
    await _safe_answer(query)
    await query.message.reply_text("➕ منوی بیشتر:", reply_markup=get_more_keyboard())
    return
