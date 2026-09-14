async def _handle_ai_noop(query, update, context, data, user_id):
    """Extracted callback branch; preserves original behavior."""
    await _safe_answer(query, "هیچ مدل فعالی تنظیم نشده است.", show_alert=True)
    return
