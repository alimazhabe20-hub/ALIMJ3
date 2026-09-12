def test_telegram_backup_optional(monkeypatch):
    import bot.db_persist as dbp
    monkeypatch.delenv("TELEGRAM_BACKUP_CHAT_ID", raising=False)
    assert dbp.telegram_backup_enabled() is False


def test_telegram_backup_chat_ids(monkeypatch):
    import bot.db_persist as dbp
    monkeypatch.setenv("TELEGRAM_BACKUP_CHAT_ID", "-100123, @backup_channel, -100456")
    assert dbp._telegram_backup_chat_ids() == [-100123, "@backup_channel", -100456]
