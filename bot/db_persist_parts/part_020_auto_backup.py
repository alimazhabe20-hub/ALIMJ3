# Auto-split part 20: auto_backup
def auto_backup():
    """Local + Telegram private-channel backup + optional GitHub."""
    results = []; remote_ok = False
    try:
        backup_db(); stable = Path(DB_PATH).parent / "bot_data.backup.db"
        local_ok = bool(stable.exists() and _validate_sqlite_backup(stable)[0])
        results.append("local:OK" if local_ok else "local:FAIL(backup artifact missing/invalid)")
    except Exception as e:
        local_ok = False; logger.error("local backup: %s", e, exc_info=True); results.append(f"local:FAIL({e})")
    if telegram_backup_enabled():
        try:
            ok, msg = telegram_upload_db(); remote_ok |= bool(ok); results.append(f"telegram:{'OK' if ok else 'FAIL'}({msg})")
        except Exception as e:
            logger.error("Telegram backup: %s", e, exc_info=True); results.append(f"telegram:FAIL({e})")
    else:
        results.append("telegram:disabled")
    if github_enabled():
        try:
            ok, msg = github_upload_db(); remote_ok |= bool(ok); results.append(f"github:{'OK' if ok else 'FAIL'}({msg})")
        except Exception as e:
            logger.error("github backup: %s", e, exc_info=True); results.append(f"github:FAIL({e})")
    else:
        results.append("github:disabled")
    return bool(local_ok or remote_ok), " | ".join(results)
