async def _handle_ai_clear_memory(query, update, context, data, user_id):
    """Extracted callback branch; preserves original behavior."""
    clear_history(user_id)
    await _safe_answer(query, "حافظه AI پاک شد ✅", show_alert=False)
    try:
        await query.edit_message_reply_markup(
            reply_markup=get_ai_keyboard(user_id)
        )
    except Exception as _exc:
        logger.debug("%s: %s", __name__, _exc)
    await query.message.reply_text("✅ حافظه گفت‌وگو و خلاصه پاک شد. (حافظه بلندمدت با «پاک کردن همه حافظه» حذف می‌شود)")
    return
