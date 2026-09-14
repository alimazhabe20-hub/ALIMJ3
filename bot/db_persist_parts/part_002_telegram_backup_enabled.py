# Auto-split part 2: telegram_backup_enabled
def telegram_backup_enabled() -> bool:
    return bool(config.BOT_TOKEN and _telegram_backup_chat_ids())
