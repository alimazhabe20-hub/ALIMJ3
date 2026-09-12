import os


def test_telegram_backup_config_optional(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BACKUP_CHAT_ID", "-1001234567890")
    import importlib
    import bot.db_persist as dp
    importlib.reload(dp)
    assert dp.telegram_backup_enabled() is True


def test_telegram_backup_disabled_without_chat(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BACKUP_CHAT_ID", raising=False)
    import importlib
    import bot.db_persist as dp
    importlib.reload(dp)
    assert dp.telegram_backup_enabled() is False


def test_auto_restore_prefers_telegram(monkeypatch):
    import importlib
    import bot.db_persist as dp
    importlib.reload(dp)
    calls=[]
    monkeypatch.setattr(dp, "telegram_backup_enabled", lambda: True)
    monkeypatch.setattr(dp, "telegram_download_pinned_db", lambda: (True, "restored"))
    monkeypatch.setattr(dp, "_user_count", lambda path: 0 if not calls else 12)
    monkeypatch.setattr(dp, "github_enabled", lambda: True)
    monkeypatch.setattr(dp, "github_download_db", lambda: calls.append("github") or (True, "github"))
    assert dp.auto_restore_if_empty() is True
    assert calls == []
