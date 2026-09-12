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
    calls = []
    state = {"users": 0}
    monkeypatch.setattr(dp, "telegram_backup_enabled", lambda: True)

    def fake_telegram_restore():
        state["users"] = 12
        return True, "restored"

    monkeypatch.setattr(dp, "telegram_download_pinned_db", fake_telegram_restore)
    monkeypatch.setattr(dp, "_user_count", lambda path: state["users"])
    monkeypatch.setattr(dp, "github_enabled", lambda: True)
    monkeypatch.setattr(dp, "github_download_db", lambda: calls.append("github") or (True, "github"))
    assert dp.auto_restore_if_empty() is True
    assert calls == []


def test_auto_restore_records_telegram_exception(monkeypatch):
    import importlib
    import bot.db_persist as dp
    importlib.reload(dp)
    monkeypatch.setattr(dp, "_user_count", lambda path: 0)
    monkeypatch.setattr(dp, "telegram_backup_enabled", lambda: True)
    monkeypatch.setattr(dp, "telegram_download_pinned_db", lambda: (_ for _ in ()).throw(RuntimeError("network down")))
    monkeypatch.setattr(dp, "github_enabled", lambda: False)
    assert dp.auto_restore_if_empty() is False
    status = dp.get_last_restore_status()
    assert "Telegram: خطای Telegram: RuntimeError: network down" in status["msg"]
    assert status["msg"] != ""


def test_auto_restore_records_success_user_count(monkeypatch):
    import importlib
    import bot.db_persist as dp
    importlib.reload(dp)
    monkeypatch.setattr(dp, "_user_count", lambda path: 7)
    assert dp.auto_restore_if_empty() is False
    status = dp.get_last_restore_status()
    assert status["ok"] is True
    assert status["local_users"] == 7
    assert "DB OK" in status["msg"]
