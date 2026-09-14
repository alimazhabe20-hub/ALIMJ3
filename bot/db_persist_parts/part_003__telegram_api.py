# Auto-split part 3: _telegram_api
def _telegram_api(method: str, **kwargs):
    url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/{method}"
    return requests.post(url, timeout=max(REMOTE_BACKUP_TIMEOUT, 30), **kwargs)
