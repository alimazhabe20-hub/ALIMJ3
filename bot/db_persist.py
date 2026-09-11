# -*- coding: utf-8 -*-
"""
بکاپ و ریستور خودکار و رایگان
  1) GitHub (GITHUB_TOKEN + GITHUB_REPO) → کاملاً خودکار
  2) تلگرام ادمین (دستی /backup و /restore)
"""
import asyncio
import base64
import os
import shutil
import sqlite3
import secrets
from datetime import datetime
from pathlib import Path

import requests

from bot.config import config
from bot.database import DB_PATH, backup_db, _user_count, get_db_connection
from bot.database_migrations import SCHEMA_VERSION
from bot.logger import logger

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
GITHUB_REPO = os.getenv("GITHUB_REPO", "").strip()  # مثال: username/bot-data-backup
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main").strip()
GITHUB_FILE = os.getenv("GITHUB_DB_FILE", "bot_data.db").strip()
API = "https://api.github.com"
REMOTE_BACKUP_TIMEOUT = max(2.0, float(os.getenv("BACKUP_REMOTE_TIMEOUT", "8")))


def _gh_headers():
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


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


def github_enabled() -> bool:
    return bool(GITHUB_TOKEN and GITHUB_REPO)


def _github_get_sha():
    url = f"{API}/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}?ref={GITHUB_BRANCH}"
    r = requests.get(url, headers=_gh_headers(), timeout=max(REMOTE_BACKUP_TIMEOUT, 20))
    if r.status_code == 200:
        return r.json().get("sha")
    return None


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


def github_upload_db():
    if not github_enabled():
        return False, "GitHub تنظیم نشده"
    path = Path(DB_PATH)
    if not path.exists():
        return False, "فایل DB نیست"
    users = _user_count(DB_PATH)
    if users == 0:
        return False, "DB خالی است — آپلود نشد"

    snap = _sqlite_snapshot_to_temp()
    if not snap:
        return False, "اسنپ‌شات SQLite ساخته نشد"
    try:
        raw = snap.read_bytes()
        # GitHub Contents API حدود ۱ مگابایت محدودیت دارد
        if len(raw) > 900_000:
            return False, (
                f"حجم DB ({len(raw)//1024}KB) برای GitHub Contents API بزرگ است. "
                "دیسک پایدار Render یا بکاپ تلگرام را فعال کن."
            )
        content_b64 = base64.b64encode(raw).decode("ascii")
        sha = _github_get_sha()
        payload = {
            "message": f"auto backup — {users} users — {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC",
            "content": content_b64,
            "branch": GITHUB_BRANCH,
        }
        if sha:
            payload["sha"] = sha
        url = f"{API}/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}"
        r = requests.put(
            url,
            headers=_gh_headers(),
            json=payload,
            timeout=max(REMOTE_BACKUP_TIMEOUT, 45),
        )
        if r.status_code in (200, 201):
            logger.info(f"GitHub backup OK ({users} users, {len(raw)} bytes)")
            return True, f"GitHub بکاپ شد ({users} کاربر)"
        # conflict sha → یکبار دیگر با sha تازه
        if r.status_code == 409:
            sha2 = _github_get_sha()
            if sha2:
                payload["sha"] = sha2
                r2 = requests.put(
                    url,
                    headers=_gh_headers(),
                    json=payload,
                    timeout=max(REMOTE_BACKUP_TIMEOUT, 45),
                )
                if r2.status_code in (200, 201):
                    logger.info(f"GitHub backup OK after sha retry ({users} users)")
                    return True, f"GitHub بکاپ شد ({users} کاربر)"
                return False, f"GitHub error {r2.status_code}: {r2.text[:200]}"
        return False, f"GitHub error {r.status_code}: {r.text[:200]}"
    except Exception as e:
        logger.error(f"github_upload: {e}")
        return False, str(e)
    finally:
        try:
            snap.unlink(missing_ok=True)
        except Exception:
            pass


def github_remote_user_count() -> int:
    """تعداد کاربر در بکاپ GitHub بدون جایگزینی DB محلی."""
    if not github_enabled():
        return 0
    try:
        url = f"{API}/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}?ref={GITHUB_BRANCH}"
        r = requests.get(url, headers=_gh_headers(), timeout=max(REMOTE_BACKUP_TIMEOUT, 20))
        if r.status_code != 200:
            return 0
        data = r.json()
        content_b64 = data.get("content", "")
        if content_b64:
            raw = base64.b64decode("".join(content_b64.split()))
        else:
            dl = data.get("download_url")
            if not dl:
                return 0
            raw = requests.get(dl, timeout=max(REMOTE_BACKUP_TIMEOUT, 30)).content
        tmp = Path(DB_PATH).with_suffix(f".db.ghprobe.{secrets.token_hex(3)}")
        try:
            tmp.write_bytes(raw)
            valid, count_or_error = _validate_sqlite_backup(tmp)
            if not valid:
                return 0
            return int(count_or_error)
        finally:
            tmp.unlink(missing_ok=True)
    except Exception as exc:
        logger.debug("github_remote_user_count failed: %s", exc)
        return 0


def github_download_db():
    if not github_enabled():
        return False, "GitHub تنظیم نشده"
    try:
        url = f"{API}/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}?ref={GITHUB_BRANCH}"
        r = requests.get(url, headers=_gh_headers(), timeout=max(REMOTE_BACKUP_TIMEOUT, 30))
        if r.status_code != 200:
            return False, f"دانلود نشد ({r.status_code})"
        data = r.json()
        content_b64 = data.get("content", "")
        if not content_b64:
            dl = data.get("download_url")
            if dl:
                raw = requests.get(dl, timeout=max(REMOTE_BACKUP_TIMEOUT, 45)).content
            else:
                return False, "محتوای خالی"
        else:
            raw = base64.b64decode("".join(content_b64.split()))
        if len(raw) < 100:
            return False, "فایل دانلودشده خیلی کوچک است"
        Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        tmp = Path(DB_PATH).with_suffix(f".db.ghdownload.{secrets.token_hex(3)}")
        tmp.write_bytes(raw)
        valid, count_or_error = _validate_sqlite_backup(tmp)
        if not valid:
            tmp.unlink(missing_ok=True)
            return False, f"بکاپ GitHub نامعتبر است: {count_or_error}"
        n = int(count_or_error)
        if n == 0:
            tmp.unlink(missing_ok=True)
            return False, "بکاپ گیت‌هاب کاربر ندارد"
        local_n = _user_count(DB_PATH) if Path(DB_PATH).exists() else 0
        if local_n > 0:
            try:
                backup_db()
            except Exception as _exc:
                logger.debug("%s: %s", __name__, _exc)
        # جایگزینی امن با backup API تا connectionهای باز نشکنند
        dest = Path(DB_PATH)
        source = sqlite3.connect(str(tmp), timeout=30)
        target = sqlite3.connect(str(dest), timeout=30)
        try:
            target.execute("PRAGMA busy_timeout=30000")
            source.backup(target)
            target.commit()
        finally:
            target.close()
            source.close()
            tmp.unlink(missing_ok=True)
        logger.warning(f"Restored from GitHub — {n} users (local was {local_n})")
        return True, f"از GitHub بازگردانی شد — {n} کاربر"
    except Exception as e:
        logger.error(f"github_download: {e}")
        return False, str(e)


# آخرین وضعیت ریستور (برای پیام ادمین)
_LAST_RESTORE_STATUS: dict[str, str | bool | int] = {
    "ok": False,
    "msg": "",
    "local_users": 0,
    "remote_users": -1,
}


def get_last_restore_status() -> dict:
    return dict(_LAST_RESTORE_STATUS)


def auto_restore_if_empty() -> bool:
    """
    ریستور خودکار:
    - اگر DB محلی خالی است → از GitHub بگیر
    - اگر GitHub کاربر بیشتری دارد → از GitHub بگیر (جلوگیری از فراموشی بعد از دیپلوی)
    """
    global _LAST_RESTORE_STATUS
    local_n = _user_count(DB_PATH) if Path(DB_PATH).exists() else 0
    _LAST_RESTORE_STATUS = {
        "ok": False,
        "msg": "",
        "local_users": local_n,
        "remote_users": -1,
    }
    if not github_enabled():
        msg = "GitHub تنظیم نشده (GITHUB_TOKEN / GITHUB_REPO)"
        logger.info("GitHub not configured — skip auto-restore")
        _LAST_RESTORE_STATUS["msg"] = msg
        return False
    if local_n == 0:
        ok, msg = github_download_db()
        logger.info(f"auto_restore (empty local): {msg}")
        _LAST_RESTORE_STATUS.update({"ok": ok, "msg": msg, "local_users": _user_count(DB_PATH)})
        return ok
    # محلی داده دارد؛ فقط اگر ریموت غنی‌تر است جایگزین کن
    try:
        remote_n = github_remote_user_count()
    except Exception:
        remote_n = 0
    _LAST_RESTORE_STATUS["remote_users"] = remote_n
    if remote_n > local_n:
        logger.warning(
            "GitHub backup has more users (%s > %s) — restoring to avoid data loss",
            remote_n, local_n,
        )
        ok, msg = github_download_db()
        logger.info(f"auto_restore (remote richer): {msg}")
        _LAST_RESTORE_STATUS.update({
            "ok": ok,
            "msg": msg,
            "local_users": _user_count(DB_PATH),
            "remote_users": remote_n,
        })
        return ok
    msg = f"DB OK — local={local_n} remote={remote_n}"
    logger.info(msg)
    _LAST_RESTORE_STATUS.update({"ok": True, "msg": msg, "local_users": local_n})
    return False


def auto_backup():
    """
    بکاپ کامل خودکار:
    1) همیشه بکاپ محلی چرخشی (backups/ + bot_data.backup.db)
    2) اگر GitHub تنظیم شده باشد، آپلود به ریپو
    برمی‌گرداند: (موفقیت_کلی, پیام_خلاصه)
    """
    results = []
    local_ok = False
    try:
        backup_db()
        local_ok = True
        results.append("local:OK")
    except Exception as e:
        logger.error(f"local backup: {e}")
        results.append(f"local:FAIL({e})")

    gh_ok = False
    if github_enabled():
        try:
            ok, msg = github_upload_db()
            gh_ok = bool(ok)
            results.append(f"github:{'OK' if ok else 'FAIL'}({msg})")
        except Exception as e:
            logger.error(f"github backup: {e}")
            results.append(f"github:FAIL({e})")
    else:
        results.append("github:disabled")

    # روی Render بدون دیسک پایدار، فقط GitHub/تلگرام نجات‌دهنده است
    overall = gh_ok or local_ok
    return overall, " | ".join(results)



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
    size_kb = path.stat().st_size / 1024
    cap = caption or (
        f"💾 بکاپ دیتابیس\n"
        f"👥 کاربران: {users}\n"
        f"📦 {size_kb:.1f} KB\n"
        f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        f"ریستور دستی: همین فایل را با کپشن /restore بفرست"
    )
    ok = 0
    for admin_id in config.ADMIN_IDS:
        try:
            with open(path, "rb") as f:
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
    detail = str(st.get("msg") or "نامشخص")
    if github_enabled():
        text = (
            "⚠️ دیتابیس بعد از استارت هنوز خالی است.\n\n"
            f"نتیجه ریستور GitHub:\n{detail}\n\n"
            "کار لازم:\n"
            "۱) آخرین فایل .db بکاپ را با کپشن /restore بفرست\n"
            "۲) GITHUB_TOKEN و GITHUB_REPO را در Render چک کن\n"
            "۳) در ریپوی بکاپ وجود فایل bot_data.db را بررسی کن\n"
            "۴) بعد از ریستور موفق، یک‌بار /backup بزن تا GitHub پر شود"
        )
    else:
        text = (
            "⚠️ دیتابیس خالی است و GitHub تنظیم نیست.\n\n"
            "GITHUB_TOKEN و GITHUB_REPO را در Render ست کن،\n"
            "یا فایل بکاپ را با کپشن /restore بفرست."
        )
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(chat_id=admin_id, text=text)
            await asyncio.sleep(0.2)
        except Exception as e:
            logger.error(f"notify empty: {e}")
