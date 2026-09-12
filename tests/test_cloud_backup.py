"""Regression tests for the off-site backup path.

The project no longer depends on Google Drive/R2.  Telegram is the primary
free off-site backup and GitHub remains optional.
"""
import importlib


def test_telegram_configuration_is_optional(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BACKUP_CHAT_ID", "-1001234567890")
    import bot.db_persist as p
    p = importlib.reload(p)
    assert p.telegram_backup_enabled() is True


def test_auto_backup_keeps_remote_failures_non_blocking(monkeypatch):
    import bot.db_persist as p
    monkeypatch.setattr(p, "backup_db", lambda: None)
    monkeypatch.setattr(p, "_user_count", lambda path: 6)
    monkeypatch.setattr(p, "_sqlite_snapshot_to_temp", lambda: None)
    monkeypatch.setattr(p, "telegram_backup_enabled", lambda: True)
    monkeypatch.setattr(p, "telegram_upload_db", lambda: (False, "telegram unavailable"))
    monkeypatch.setattr(p, "github_enabled", lambda: False)
    ok, msg = p.auto_backup()
    assert ok is False  # both local artifact and remote upload are mocked as unavailable
    assert "telegram:FAIL" in msg


def test_empty_restore_prefers_telegram(monkeypatch):
    import bot.db_persist as p
    calls = []
    monkeypatch.setattr(p, "_user_count", lambda path: 0)
    monkeypatch.setattr(p, "telegram_backup_enabled", lambda: True)
    monkeypatch.setattr(p, "telegram_download_pinned_db", lambda: (True, "restored 6 users"))
    monkeypatch.setattr(p, "github_enabled", lambda: True)
    monkeypatch.setattr(p, "github_download_db", lambda: calls.append("github") or (True, "github"))
    assert p.auto_restore_if_empty() is True
    assert calls == []
