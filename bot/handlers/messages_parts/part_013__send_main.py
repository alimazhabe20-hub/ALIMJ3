async def _send_main(update, context, text, user_id):
    context.user_data.pop("waiting_for", None)
    await update.message.reply_text("🏠 منوی اصلی", reply_markup=get_main_keyboard(user_id))
    msg = await update.message.reply_text(text, reply_markup=get_refresh_button())
    context.user_data["last_main_msg_id"] = msg.message_id
    set_last_main_msg_id(user_id, msg.message_id)
    return msg
