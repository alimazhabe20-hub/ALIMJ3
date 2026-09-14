# Auto-split part 1: _telegram_backup_chat_ids
def _telegram_backup_chat_ids() -> list[str]:
    """Return configured Telegram backup chat IDs, accepting comma/newline separated values."""
    raw = os.getenv("TELEGRAM_BACKUP_CHAT_ID", TELEGRAM_BACKUP_CHAT_ID).strip()
    return [item.strip() for item in re.split(r"[,\n;]+", raw) if item.strip()]
