async def _handle_back_to_main(query, update, context, data, user_id):
    """Extracted callback branch; preserves original behavior."""
    await _safe_answer(query)
    try:
        user_row = get_user(user_id)
        first_name = (
            (user_row[1] if user_row and len(user_row) > 1 and user_row[1] else None)
            or "کاربر"
        )
        try:
            city = get_user_city(user_id) or "قم"
        except Exception:
            city = "قم"

        try:
            message = await build_message(user_id, first_name, city)
        except Exception as e:
            logger.error(
                f"build_message failed in back_to_main: {type(e).__name__}: {e}",
                exc_info=True,
            )
            message = (
                f"🌟 سلام {first_name} عزیز!\n\n"
                f"⚠️ بارگذاری کامل اطلاعات با خطا مواجه شد.\n"
                f"دستور /start را بفرستید.\n"
                f"({type(e).__name__})"
            )

        if len(message) > 4000:
            message = message[:3990] + "\n…"

        sent = False
        # 1) ویرایش همان پیام
        try:
            await query.edit_message_text(message, reply_markup=get_refresh_button())
            context.user_data["last_main_msg_id"] = query.message.message_id
            try:
                set_last_main_msg_id(user_id, query.message.message_id)
            except Exception as _exc:
                logger.debug("%s: %s", __name__, _exc)
            sent = True
        except Exception as e1:
            logger.warning(f"back_to_main edit failed: {type(e1).__name__}: {e1}")

        # 2) اگر edit نشد، پیام جدید با bot.send_message
        if not sent:
            try:
                msg = await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=message,
                    reply_markup=get_refresh_button(),
                )
                context.user_data["last_main_msg_id"] = msg.message_id
                try:
                    set_last_main_msg_id(user_id, msg.message_id)
                except Exception as _exc:
                    logger.debug("%s: %s", __name__, _exc)
                sent = True
                try:
                    await query.message.delete()
                except Exception as _exc:
                    logger.debug("%s: %s", __name__, _exc)
            except Exception as e2:
                logger.error(
                    f"back_to_main send failed: {type(e2).__name__}: {e2}",
                    exc_info=True,
                )

        # کیبورد اصلی پایین
        try:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="",
                reply_markup=get_main_keyboard(user_id),
            )
        except Exception as _exc:
            logger.debug("%s: %s", __name__, _exc)

        if not sent:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="⚠️ بازگشت به منو ناموفق بود. لطفاً /start را بفرستید.",
            )
    except Exception as e:
        logger.error(f"back_to_main outer error: {type(e).__name__}: {e}", exc_info=True)
        try:
            chat_id = update.effective_chat.id if update.effective_chat else None
            if chat_id:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "⚠️ موقتاً مشکلی پیش آمد. دستور /start را بفرستید.\n"
                        f"کد خطا: {type(e).__name__}"
                    ),
                )
        except Exception as _exc:
            logger.debug("%s: %s", __name__, _exc)
    return
