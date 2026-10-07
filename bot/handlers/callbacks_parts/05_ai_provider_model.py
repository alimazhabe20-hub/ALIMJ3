async def _handle_ai_provider_model(query, update, context, data, user_id):
    """Extracted callback branch; preserves original behavior."""
    try:
        index = int(data.split(":", 1)[1])
        providers = available_providers()
        provider, label = providers[index]
    except (ValueError, IndexError):
        await _safe_answer(query, "❌ این سرویس دیگر در دسترس نیست.", show_alert=True)
        return
    set_selected_provider(user_id, provider)
    await _safe_answer(query, f"✅ فعال شد: {label}", show_alert=False)
    await query.edit_message_reply_markup(reply_markup=get_ai_keyboard(user_id))
    return
