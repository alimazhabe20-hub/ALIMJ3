async def _handle_ai_models(query, update, context, data, user_id):
    """Extracted callback branch; preserves original behavior."""
    await _safe_answer(query)
    await query.edit_message_reply_markup(reply_markup=get_ai_model_keyboard(user_id))
    return
