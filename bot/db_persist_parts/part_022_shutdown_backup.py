# Auto-split part 22: shutdown_backup
def shutdown_backup(reason: str = "shutdown"):
    """
    بکاپ هوشمند قبل از دیپلوی / خاموش شدن:
    1) اسنپ‌شات محلی
    2) آپلود GitHub با چند بار تلاش
    3) ارسال به ادمین تلگرام
    Render قبل از دیپلوی جدید SIGTERM می‌فرستد؛ این تابع همان لحظه اجرا می‌شود.
    """
    users = _user_count(DB_PATH) if Path(DB_PATH).exists() else 0
    results = [f"reason={reason}", f"users={users}"]
    if users == 0:
        logger.warning("shutdown_backup: DB has 0 users — nothing to persist")
        results.append("skip:empty-db")
        return " | ".join(results)

    try:
        backup_db()
        results.append("local:OK")
    except Exception as e:
        results.append(f"local:FAIL({e})")
        logger.error("shutdown local backup: %s", e)

    if telegram_backup_enabled():
        tg_ok = False; last_msg = ""
        for attempt in range(1, 4):
            try:
                tg_ok, last_msg = telegram_upload_db()
                if tg_ok:
                    results.append(f"telegram_channel:OK(try={attempt})")
                    break
            except Exception as e:
                last_msg = str(e); logger.error("shutdown Telegram channel try %s error: %s", attempt, e)
            time.sleep(min(1.5 * attempt, 4))
        if not tg_ok: results.append(f"telegram_channel:FAIL({last_msg})")
    else:
        results.append("telegram_channel:disabled")

    if github_enabled():
        gh_ok = False
        last_msg = ""
        for attempt in range(1, 4):
            try:
                ok, msg = github_upload_db()
                last_msg = msg
                if ok:
                    gh_ok = True
                    results.append(f"github:OK(try={attempt})")
                    break
                logger.warning("shutdown GitHub try %s failed: %s", attempt, msg)
            except Exception as e:
                last_msg = str(e)
                logger.error("shutdown GitHub try %s error: %s", attempt, e)
            try:
                import time as _time
                _time.sleep(min(1.5 * attempt, 4))
            except Exception:
                pass
        if not gh_ok:
            results.append(f"github:FAIL({last_msg})")
    else:
        results.append("github:disabled")

    try:
        ok, msg = send_db_to_admins_sync(
            caption=(
                "💾 بکاپ خودکار قبل از دیپلوی / خاموش شدن\n"
                f"📌 دلیل: {reason}\n"
                f"👥 کاربران: {users}\n"
                f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
                "نسخه جدید در حال بالا آمدن است.\n"
                "برای ریستور دستی: همین فایل را با کپشن /restore بفرست."
            )
        )
        results.append(f"telegram:{'OK' if ok else 'FAIL'}({msg})")
        logger.info("shutdown_backup Telegram: %s", msg)
    except Exception as e:
        results.append(f"telegram:FAIL({e})")
        logger.error("shutdown_backup Telegram: %s", e)

    summary = " | ".join(results)
    logger.info("shutdown_backup done: %s", summary)
    return summary
