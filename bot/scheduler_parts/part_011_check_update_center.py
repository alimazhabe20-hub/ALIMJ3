# Auto-split part 11: check_update_center
async def check_update_center(context):
    """Periodic read-only release check; alerts admins only for a new release."""
    try:
        from bot.services.update_center import check_for_updates, maybe_notify_admins
        result = await asyncio.to_thread(check_for_updates, force=True)
        loop = asyncio.get_running_loop()
        await asyncio.to_thread(
            maybe_notify_admins,
            result,
            lambda admin_id, text: asyncio.run_coroutine_threadsafe(
                context.bot.send_message(chat_id=admin_id, text=text),
                loop,
            ).result(timeout=15),
        )
    except Exception as exc:
        logger.debug("update center periodic check failed: %s", exc)
