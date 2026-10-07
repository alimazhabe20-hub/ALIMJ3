async def _handle_calendar_day(query, update, context, data, user_id):
    """Extracted callback branch; preserves original behavior."""
    await _safe_answer(query)
    parts = data.split("_")
    year, month, day = int(parts[1]), int(parts[2]), int(parts[3])
    try:
        jdatetime.date(year, month, day)
    except ValueError:
        if day < 1:
            month -= 1
            if month < 1:
                month = 12
                year -= 1
            last_day = jdatetime.date(year, month, 1) - jdatetime.timedelta(days=1)
            day = last_day.day
        else:
            month += 1
            if month > 12:
                month = 1
                year += 1
            day = 1
    text = get_calendar_text(year, month, day, user_id)
    await query.edit_message_text(
        text,
        reply_markup=get_calendar_buttons(year, month, day, user_id)
    )
    return
