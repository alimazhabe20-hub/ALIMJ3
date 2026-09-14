# Auto-split part 24: restore_db_from_file
async def restore_db_from_file(file_path: str):
    src = Path(file_path)
    valid, count_or_error = _validate_sqlite_backup(src)
    if not valid:
        return False, f"فایل بکاپ معتبر نیست: {count_or_error}"
    n = int(count_or_error)

    if Path(DB_PATH).exists() and _user_count(DB_PATH) > 0:
        try:
            backup_db()
        except Exception:
            logger.warning("Could not create pre-restore backup", exc_info=True)

    dest = Path(DB_PATH)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(f".db.restoring.{secrets.token_hex(6)}")
    try:
        shutil.copy2(src, tmp)
        valid, count_or_error = _validate_sqlite_backup(tmp)
        if not valid:
            return False, f"فایل بکاپ معتبر نیست: {count_or_error}"
        # Keep the live database inode stable. SQLite's backup API replaces
        # database contents atomically at the SQLite level and avoids leaving
        # already-open connections attached to the old inode.
        source = sqlite3.connect(str(tmp), timeout=REMOTE_BACKUP_TIMEOUT)
        target = sqlite3.connect(str(dest), timeout=REMOTE_BACKUP_TIMEOUT)
        try:
            target.execute("PRAGMA busy_timeout=30000")
            source.backup(target)
            target.commit()
        finally:
            target.close()
            source.close()
    except Exception:
        logger.exception("Database restore failed")
        return False, "بازگردانی فایل دیتابیس انجام نشد"
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except Exception as _exc:
            logger.debug("%s: %s", __name__, _exc)

    if telegram_backup_enabled():
        try: telegram_upload_db()
        except Exception: logger.warning("Post-restore Telegram backup failed", exc_info=True)
    if github_enabled():
        try:
            github_upload_db()
        except Exception:
            logger.warning("Post-restore GitHub backup failed", exc_info=True)
    return True, f"✅ بازگردانی موفق — {n} کاربر"
