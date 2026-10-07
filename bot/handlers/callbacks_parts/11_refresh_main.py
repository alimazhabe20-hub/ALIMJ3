async def _handle_refresh_main(query, update, context, data, user_id):
    """Extracted callback branch; preserves original behavior."""
    from bot.logger import logger

    lock = _get_refresh_lock(user_id)

    if lock.locked():
        await _safe_answer(query, "⏳ بروزرسانی قبلی هنوز در حال انجام است.", show_alert=False)
        return

    async with lock:
        await _safe_answer(query, "🔄 در حال بروزرسانی...", show_alert=False)

        chat_id = None
        message_id = None
        try:
            if query.message is not None:
                chat_id = query.message.chat_id
                message_id = query.message.message_id
            elif update.effective_chat is not None:
                chat_id = update.effective_chat.id
        except Exception as e:
            logger.warning("refresh_main resolve chat: %s", e)
            try:
                chat_id = update.effective_chat.id if update.effective_chat else None
            except Exception:
                chat_id = None

        try:
            user_row = None
            try:
                user_row = get_user(user_id)
            except Exception as e:
                logger.warning("refresh_main get_user: %s", e)

            first_name = "کاربر"
            try:
                if user_row and len(user_row) > 1 and user_row[1]:
                    first_name = str(user_row[1])
            except Exception as _exc:
                logger.debug("%s: %s", __name__, _exc)

            city = "قم"
            try:
                city = get_user_city(user_id) or "قم"
            except Exception as e:
                logger.warning("refresh_main get_user_city: %s", e)

            try:
                message = await build_message(user_id, first_name, city)
            except Exception as e:
                logger.error("refresh_main build_message: %s", e, exc_info=True)
                message = (
                    f"🌟 سلام {first_name} عزیز!\n\n"
                    f"⚠️ بارگذاری اطلاعات با خطا مواجه شد.\n"
                    f"کد: {type(e).__name__}\n"
                    f"/start را بفرستید."
                )

            if not message:
                message = "⚠️ محتوا خالی بود. /start را بفرستید."
            if len(message) > 4000:
                message = message[:3990] + "\n…"

            sent = False

            # روش ۱: edit از طریق callback_query
            if not sent:
                try:
                    await query.edit_message_text(
                        text=message,
                        reply_markup=get_refresh_button(),
                    )
                    sent = True
                    if message_id:
                        context.user_data["last_main_msg_id"] = message_id
                        try:
                            set_last_main_msg_id(user_id, message_id)
                        except Exception as _exc:
                            logger.debug("%s: %s", __name__, _exc)
                except BadRequest as e:
                    err = str(e).lower()
                    if "message is not modified" in err or "not modified" in err:
                        sent = True
                    else:
                        logger.warning("refresh_main query.edit BadRequest: %s", e)
                except Exception as e:
                    logger.warning("refresh_main query.edit: %s", e)

            # روش ۲: edit مستقیم با bot API
            if not sent and chat_id and message_id:
                try:
                    await context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=message,
                        reply_markup=get_refresh_button(),
                    )
                    sent = True
                    context.user_data["last_main_msg_id"] = message_id
                    try:
                        set_last_main_msg_id(user_id, message_id)
                    except Exception as _exc:
                        logger.debug("%s: %s", __name__, _exc)
                except BadRequest as e:
                    err = str(e).lower()
                    if "message is not modified" in err or "not modified" in err:
                        sent = True
                    else:
                        logger.warning("refresh_main bot.edit BadRequest: %s", e)
                except Exception as e:
                    logger.warning("refresh_main bot.edit: %s", e)

            # روش ۳: ارسال پیام جدید
            if not sent and chat_id:
                try:
                    msg = await context.bot.send_message(
                        chat_id=chat_id,
                        text=message,
                        reply_markup=get_refresh_button(),
                    )
                    sent = True
                    context.user_data["last_main_msg_id"] = msg.message_id
                    try:
                        set_last_main_msg_id(user_id, msg.message_id)
                    except Exception as _exc:
                        logger.debug("%s: %s", __name__, _exc)
                    if message_id:
                        try:
                            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
                        except Exception as _exc:
                            logger.debug("%s: %s", __name__, _exc)
                except Exception as e:
                    logger.error("refresh_main send: %s", e, exc_info=True)

            if not sent:
                tip = "⚠️ بروزرسانی انجام نشد."
                if chat_id:
                    tip += " لطفاً /start را بفرستید."
                else:
                    tip += " چت پیدا نشد؛ /start را بفرستید."
                try:
                    if chat_id:
                        await context.bot.send_message(chat_id=chat_id, text=tip)
                except Exception as _exc:
                    logger.debug("%s: %s", __name__, _exc)

        except Exception as e:
            logger.error("refresh_main outer: %s", e, exc_info=True)
            try:
                cid = chat_id
                if cid is None and update.effective_chat:
                    cid = update.effective_chat.id
                if cid:
                    await context.bot.send_message(
                        chat_id=cid,
                        text=(
                            "⚠️ بروزرسانی موقتاً ناموفق بود.\n"
                            f"کد خطا: {type(e).__name__}: {str(e)[:120]}\n"
                            "چند ثانیه بعد دوباره بزنید یا /start بفرستید."
                        ),
                    )
            except Exception as _exc:
                logger.debug("%s: %s", __name__, _exc)
    return
