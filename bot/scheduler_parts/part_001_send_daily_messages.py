# Auto-split part 1: send_daily_messages
async def send_daily_messages(context):
    logger.info("Starting daily broadcast...")
    users = get_all_users()
    count = 0
    for user_id, first_name, city, lang in users:
        try:
            msg = await build_message(user_id, first_name, city)
            await context.bot.send_message(
                chat_id=user_id,
                text=msg,
                reply_markup=get_refresh_button()
            )
            count += 1
            await asyncio.sleep(0.2)
        except Exception as e:
            logger.error(f"Failed to send to {user_id}: {e}")
    logger.info(f"Daily broadcast sent to {count}/{len(users)} users")
