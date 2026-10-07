async def _handle_calendar_nav(query, update, context, data, user_id):
    """Extracted callback branch; preserves original behavior."""
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
