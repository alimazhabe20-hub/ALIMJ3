# Auto-split part 7: periodic_telegram_backup
async def periodic_telegram_backup(context):
    """یک کپی مستقل روی چت ادمین‌ها، با فاصله طولانی‌تر."""
    try:
        from bot.db_persist import send_db_to_admins, auto_backup
        ok, msg = auto_backup()
        ok2, msg2 = await send_db_to_admins(
            context.bot,
            caption=(
                "💾 بکاپ خودکار دوره‌ای\n"
                f"وضعیت: {msg}\n"
                f"🕐 {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}"
            ),
        )
        logger.info("telegram backup: %s", msg2)
    except Exception as e:
        logger.error("telegram periodic backup failed: %s", e, exc_info=True)
