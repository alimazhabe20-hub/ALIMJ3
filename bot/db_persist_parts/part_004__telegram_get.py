# Auto-split part 4: _telegram_get
def _telegram_get(method: str, **kwargs):
    url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/{method}"
    return requests.get(url, timeout=max(REMOTE_BACKUP_TIMEOUT, 30), **kwargs)
