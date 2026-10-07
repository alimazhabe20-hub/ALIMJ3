"""db_persist: backup responsibilities."""
from .db_persist_common import *  # noqa: F401,F403
from . import db_persist_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


def _validate_sqlite_backup(path: Path) -> tuple[bool, str]:
    """Validate a candidate DB before it can replace the live database."""
    try:
        if path.stat().st_size < 100:
            return False, "فایل خیلی کوچک است"
        max_bytes = max(1024 * 1024, int(getattr(config, "RESTORE_MAX_BYTES", 256 * 1024 * 1024)))
        if path.stat().st_size > max_bytes:
            return False, "حجم فایل بیش از حد مجاز است"
        uri = f"file:{path.resolve()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=5)
        try:
            integrity = conn.execute("PRAGMA integrity_check").fetchone()
            if not integrity or str(integrity[0]).lower() != "ok":
                return False, "integrity_check ناموفق بود"
            conn.execute("PRAGMA foreign_key_check").fetchall()
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            required = {"users", "stats"}
            if not required.issubset(tables):
                return False, "ساختار دیتابیس با نسخه فعلی سازگار نیست"
            user_cols = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
            required_user_cols = {
                "user_id", "first_name", "city", "country", "language", "subscribed",
                "register_date", "last_active", "notification_enabled", "notify_fajr",
                "notify_dhuhr", "notify_asr", "notify_maghrib", "notify_isha", "birth_date",
            }
            if not required_user_cols.issubset(user_cols):
                return False, "ستون‌های دیتابیس با نسخه فعلی سازگار نیست"
            stats_cols = {r[1] for r in conn.execute("PRAGMA table_info(stats)")}
            if not {"id", "date", "total_users", "active_users"}.issubset(stats_cols):
                return False, "ساختار جدول stats ناسازگار است"
            meta_exists = "schema_meta" in tables
            if meta_exists:
                row = conn.execute("SELECT value FROM schema_meta WHERE key='schema_version'").fetchone()
                if row is not None:
                    try:
                        version = int(row[0])
                    except (TypeError, ValueError):
                        return False, "schema_version نامعتبر است"
                    if version > SCHEMA_VERSION:
                        return False, "نسخه schema این بکاپ جدیدتر از نسخه فعلی است"
            users = int(conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] or 0)
            return True, str(users)
        finally:
            conn.close()
    except Exception:
        return False, "فایل SQLite معتبر نیست"

def _sqlite_snapshot_to_temp() -> Path | None:
    """اسنپ‌شات امن SQLite (شامل WAL) به فایل موقت — برای آپلود/ارسال."""
    src_path = Path(DB_PATH)
    if not src_path.exists():
        return None
    tmp = src_path.with_suffix(f".db.snap.{secrets.token_hex(4)}")
    try:
        src = sqlite3.connect(str(src_path), timeout=30, check_same_thread=False)
        try:
            # ادغام WAL قبل از بکاپ تا چیزی جا نماند
            try:
                src.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            except Exception:
                pass
            dst = sqlite3.connect(str(tmp), timeout=30, check_same_thread=False)
            try:
                src.backup(dst)
                dst.commit()
            finally:
                dst.close()
        finally:
            src.close()
        if tmp.stat().st_size < 100:
            tmp.unlink(missing_ok=True)
            return None
        return tmp
    except Exception as exc:
        logger.error("sqlite snapshot failed: %s", exc)
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass
        return None

def get_last_restore_status() -> dict:
    return dict(_LAST_RESTORE_STATUS)

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

def send_db_to_admins_sync(caption: str = None):
    """
    ارسال همگام فایل DB به ادمین با HTTP مستقیم.
    برای لحظه خاموش شدن / دیپلوی قابل اعتمادتر از async است.
    """
    path = Path(DB_PATH)
    if not path.exists():
        return False, "فایل DB نیست"
    if not config.ADMIN_IDS:
        return False, "ADMIN_IDS خالی است"
    if not config.BOT_TOKEN:
        return False, "BOT_TOKEN نیست"

    try:
        backup_db()
    except Exception as _exc:
        logger.debug("%s: %s", __name__, _exc)

    users = _user_count(DB_PATH)
    # اسنپ‌شات امن به‌جای خواندن مستقیم فایل WAL
    snap = _sqlite_snapshot_to_temp()
    send_path = snap if snap else path
    size_kb = send_path.stat().st_size / 1024
    cap = caption or (
        f"💾 بکاپ خودکار (قبل از دیپلوی / خاموش شدن)\n"
        f"👥 کاربران: {users}\n"
        f"📦 {size_kb:.1f} KB\n"
        f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )

    url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendDocument"
    ok = 0
    errors = []
    try:
        for admin_id in config.ADMIN_IDS:
            try:
                with open(send_path, "rb") as f:
                    r = requests.post(
                        url,
                        data={"chat_id": admin_id, "caption": cap},
                        files={"document": (f"bot_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db", f)},
                        timeout=max(REMOTE_BACKUP_TIMEOUT, 45),
                    )
                if r.status_code == 200 and r.json().get("ok"):
                    ok += 1
                else:
                    errors.append(f"{admin_id}:{r.status_code} {r.text[:120]}")
            except Exception as e:
                errors.append(f"{admin_id}:{e}")
                logger.error(f"sync send backup to {admin_id}: {e}")
    finally:
        if snap:
            try:
                snap.unlink(missing_ok=True)
            except Exception:
                pass

    msg = f"ارسال sync به {ok}/{len(config.ADMIN_IDS)} ادمین"
    if errors:
        msg += " | " + "; ".join(errors)[:200]
    return ok > 0, msg

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

async def send_db_to_admins(bot, caption: str = None):
    path = Path(DB_PATH)
    if not path.exists():
        return False, "فایل دیتابیس وجود ندارد"
    try:
        backup_db()
    except Exception as _exc:
        logger.debug("%s: %s", __name__, _exc)
    users = _user_count(DB_PATH)
    snap = _sqlite_snapshot_to_temp()
    send_path = snap if snap else path
    size_kb = send_path.stat().st_size / 1024
    cap = caption or (
        f"💾 بکاپ دیتابیس\n"
        f"👥 کاربران: {users}\n"
        f"📦 {size_kb:.1f} KB\n"
        f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        f"ریستور دستی: همین فایل را با کپشن /restore بفرست"
    )
    ok = 0
    try:
        for admin_id in config.ADMIN_IDS:
            try:
                with open(send_path, "rb") as f:
                    await bot.send_document(
                        chat_id=admin_id,
                        document=f,
                        filename=f"bot_backup_{datetime.now().strftime('%Y%m%d_%H%M')}.db",
                        caption=cap,
                    )
                ok += 1
                await asyncio.sleep(0.3)
            except Exception as e:
                logger.error(f"Send backup to admin {admin_id}: {e}")
    finally:
        if snap:
            try:
                snap.unlink(missing_ok=True)
            except Exception:
                pass
    return ok > 0, f"ارسال به {ok}/{len(config.ADMIN_IDS)} ادمین ({users} کاربر)"

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

async def notify_admins_if_empty(bot):
    n = _user_count(DB_PATH)
    if n > 0:
        return
    if not config.ADMIN_IDS:
        return
    st = get_last_restore_status()
    detail = str(st.get("msg") or "ریستور اجرا نشد یا وضعیت آن ثبت نشده است؛ لاگ startup auto-restore را بررسی کن.")
    if telegram_backup_enabled() or github_enabled():
        text = (
            "⚠️ دیتابیس بعد از استارت هنوز خالی است.\n\n"
            f"نتیجه ریستور خودکار:\n{detail}\n\n"
            "اگر ریستور خودکار ناموفق بود، کانال بکاپ و TELEGRAM_BACKUP_CHAT_ID را بررسی کن.\n"
            "ریستور دستی /restore همچنان به‌عنوان راه اضطراری فعال است."
        )
    else:
        text = (
            "⚠️ دیتابیس خالی است و بکاپ خودکار تنظیم نشده.\n\n"
            "TELEGRAM_BACKUP_CHAT_ID را در Render تنظیم کن."
        )
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(chat_id=admin_id, text=text)
            await asyncio.sleep(0.2)
        except Exception as e:
            logger.error(f"notify empty: {e}")
