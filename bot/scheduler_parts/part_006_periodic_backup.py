# Auto-split part 6: periodic_backup
async def periodic_backup(context):
    """بکاپ خودکار پرتکرار: local + Telegram private channel + optional GitHub."""
    try:
        from bot.db_persist import auto_backup
        ok, msg = auto_backup()
        logger.info("auto_backup: %s", msg)
    except Exception as e:
        logger.error("periodic backup error: %s", e, exc_info=True)
