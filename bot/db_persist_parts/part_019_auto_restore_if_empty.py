# Auto-split part 19: auto_restore_if_empty
def auto_restore_if_empty() -> bool:
    """Restore automatically: pinned Telegram backup first, GitHub second.

    Every exit path records a human-readable status so the admin notification
    can never fall back to the misleading "نامشخص" message.
    """
    global _LAST_RESTORE_STATUS
    try:
        local_n = _user_count(DB_PATH)
    except Exception as exc:
        local_n = 0
        _LAST_RESTORE_STATUS = {
            "ok": False, "msg": f"خطا در بررسی دیتابیس محلی: {type(exc).__name__}: {exc}",
            "local_users": 0, "remote_users": -1,
        }
        logger.error("auto_restore_if_empty local DB check failed", exc_info=True)
        return False

    _LAST_RESTORE_STATUS = {
        "ok": local_n > 0,
        "msg": f"DB OK — local={local_n}" if local_n > 0 else "در حال بررسی بکاپ‌های خودکار...",
        "local_users": local_n,
        "remote_users": -1,
    }
    if local_n == 0:
        attempts = []
        if telegram_backup_enabled():
            try:
                ok, msg = telegram_download_pinned_db()
                attempts.append(f"Telegram: {msg}")
                if ok:
                    restored_n = _user_count(DB_PATH)
                    _LAST_RESTORE_STATUS.update({"ok": restored_n > 0, "msg": msg, "local_users": restored_n})
                    if restored_n > 0:
                        return True
                    attempts.append("Telegram: فایل دریافت شد ولی دیتابیس محلی همچنان ۰ کاربر دارد")
            except Exception as exc:
                msg = f"خطای Telegram: {type(exc).__name__}: {exc}"
                attempts.append(f"Telegram: {msg}")
                logger.error("auto_restore_if_empty Telegram restore failed", exc_info=True)
        else:
            attempts.append("Telegram: غیرفعال (TELEGRAM_BACKUP_CHAT_ID تنظیم نشده)")

        if github_enabled():
            try:
                ok, msg = github_download_db()
                attempts.append(f"GitHub: {msg}")
                if ok:
                    restored_n = _user_count(DB_PATH)
                    _LAST_RESTORE_STATUS.update({"ok": restored_n > 0, "msg": msg, "local_users": restored_n})
                    if restored_n > 0:
                        return True
                    attempts.append("GitHub: فایل دریافت شد ولی دیتابیس محلی همچنان ۰ کاربر دارد")
            except Exception as exc:
                msg = f"خطای GitHub: {type(exc).__name__}: {exc}"
                attempts.append(f"GitHub: {msg}")
                logger.error("auto_restore_if_empty GitHub restore failed", exc_info=True)
        else:
            attempts.append("GitHub: غیرفعال")

        _LAST_RESTORE_STATUS.update({
            "ok": False,
            "msg": " | ".join(attempts) if attempts else "هیچ بکاپ خودکاری تنظیم نشده",
            "local_users": 0,
        })
        return False

    logger.info("DB OK — local=%s", local_n)
    _LAST_RESTORE_STATUS.update({"ok": True, "msg": f"DB OK — local={local_n}", "local_users": local_n})
    return False
