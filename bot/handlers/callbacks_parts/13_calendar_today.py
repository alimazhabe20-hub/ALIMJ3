async def _handle_calendar_today(query, update, context, data, user_id):
    """Extracted callback branch; preserves original behavior."""
    await _safe_answer(query)
    today = get_today_tehran()
    text = get_calendar_text(today.year, today.month, today.day, user_id)
    await query.edit_message_text(
        text,
        reply_markup=get_calendar_buttons(today.year, today.month, today.day, user_id)
    )
    return
