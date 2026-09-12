# -*- coding: utf-8 -*-
"""
بکاپ و ریستور خودکار و رایگان
  1) Telegram خصوصی → کپی خارج از سرور و بدون کارت
  2) Local → چرخش بکاپ روی دیسک موجود
  3) GitHub → فقط در صورت تنظیم، به‌عنوان fallback اختیاری
"""
import asyncio
import base64
import os
import shutil
import sqlite3
import secrets
import gzip
import time
import re
import uuid
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
GITHUB_FILE = os.getenv("GITHUB_DB_FILE", "backups/latest.db.gz").strip().lstrip("/")
API = "https://api.github.com"
GITHUB_RETRIES = max(1, int(os.getenv("GITHUB_BACKUP_RETRIES", "4")))
GITHUB_BACKOFF = max(0.5, float(os.getenv("GITHUB_BACKUP_BACKOFF", "1.5")))
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


def _normalized_repo() -> str:
    """Normalize owner/repo and reject accidental URL forms."""
    value = GITHUB_REPO.strip().strip("/")
    value = re.sub(r"^https?://github\.com/", "", value, flags=re.I)
    value = value.removesuffix(".git").strip("/")
    return value


def github_enabled() -> bool:
    return bool(GITHUB_TOKEN and _normalized_repo()) and _normalized_repo().count("/") == 1


def _github_request(method: str, url: str, **kwargs):
    """GitHub request with retry for transient failures and rate limits."""
    last = None
    for attempt in range(1, GITHUB_RETRIES + 1):
        try:
            r = requests.request(
                method, url, headers=_gh_headers(),
                timeout=kwargs.pop("timeout", max(REMOTE_BACKUP_TIMEOUT, 30)),
                **kwargs,
            )
            if r.status_code in {429, 500, 502, 503, 504}:
                last = r
                retry_after = r.headers.get("Retry-After")
                delay = float(retry_after) if retry_after and retry_after.replace('.', '', 1).isdigit() else GITHUB_BACKOFF * attempt
                time.sleep(min(delay, 12))
                continue
            return r
        except requests.RequestException as exc:
            last = exc
            if attempt < GITHUB_RETRIES:
                time.sleep(min(GITHUB_BACKOFF * attempt, 8))
    if isinstance(last, requests.Response):
        return last
    raise last if isinstance(last, Exception) else RuntimeError("GitHub request failed")


def _github_repo_check():
    repo = _normalized_repo()
    if not github_enabled():
        return False, "GITHUB_TOKEN/GITHUB_REPO تنظیم نشده یا GITHUB_REPO باید owner/repo باشد"
    url = f"{API}/repos/{repo}"
    try:
        r = _github_request("GET", url, timeout=max(REMOTE_BACKUP_TIMEOUT, 20))
        if r.status_code == 200:
            data = r.json()
            if data.get("archived"):
                return False, "Repository آرشیو شده است"
            if data.get("private") is not True:
                return False, "Repository بکاپ باید Private باشد تا اطلاعات کاربران عمومی نشود"
            return True, "GitHub repository OK"
        if r.status_code == 404:
            return False, "GitHub 404: repository پیدا نشد یا Token به آن دسترسی ندارد (owner/repo و دسترسی Contents را بررسی کن)"
        if r.status_code in (401, 403):
            return False, f"GitHub {r.status_code}: Token نامعتبر یا فاقد دسترسی Repository/Contents است"
        return False, f"GitHub repository check {r.status_code}: {r.text[:220]}"
    except Exception as exc:
        return False, f"GitHub connection error: {exc}"


def _github_get_sha():
    repo = _normalized_repo()
    url = f"{API}/repos/{repo}/contents/{GITHUB_FILE}?ref={GITHUB_BRANCH}"
    r = _github_request("GET", url, timeout=max(REMOTE_BACKUP_TIMEOUT, 20))
    if r.status_code == 200:
        return r.json().get("sha")
    if r.status_code in (404,):
        return None
    raise RuntimeError(f"GitHub lookup {r.status_code}: {r.text[:220]}")


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
    """Upload a compressed, validated SQLite snapshot to a private GitHub repo."""
    if not github_enabled():
        return False, "GitHub تنظیم نشده یا GITHUB_REPO نامعتبر است"
    repo_ok, repo_msg = _github_repo_check()
    if not repo_ok:
        return False, repo_msg
    users = _user_count(DB_PATH)
    if users == 0:
        return False, "DB خالی است — آپلود نشد"

    snap = _sqlite_snapshot_to_temp()
    if not snap:
        return False, "اسنپ‌شات SQLite ساخته نشد"
    compressed = snap.with_suffix(snap.suffix + ".gz")
    try:
        with open(snap, "rb") as src, gzip.open(compressed, "wb", compresslevel=6) as dst:
            shutil.copyfileobj(src, dst)
        raw = compressed.read_bytes()
        # Contents API is unsuitable for large files; compression usually keeps DBs well below this limit.
        if len(raw) > 900_000:
            return False, f"بکاپ فشرده هنوز {len(raw)//1024}KB است؛ برای GitHub Contents API بزرگ است"
        content_b64 = base64.b64encode(raw).decode("ascii")
        sha = _github_get_sha()
        payload = {
            "message": f"auto backup — {users} users — {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC",
            "content": content_b64,
            "branch": GITHUB_BRANCH,
        }
        if sha:
            payload["sha"] = sha
        repo = _normalized_repo()
        url = f"{API}/repos/{repo}/contents/{GITHUB_FILE}"
        r = _github_request("PUT", url, json=payload, timeout=max(REMOTE_BACKUP_TIMEOUT, 45))
        if r.status_code in (200, 201):
            logger.info("GitHub backup OK (%s users, %s compressed bytes)", users, len(raw))
            return True, f"GitHub:OK ({users} کاربر، {len(raw)//1024}KB)"
        if r.status_code == 409:
            # Another backup may have updated the same path; refresh SHA once.
            sha2 = _github_get_sha()
            if sha2:
                payload["sha"] = sha2
                r2 = _github_request("PUT", url, json=payload, timeout=max(REMOTE_BACKUP_TIMEOUT, 45))
                if r2.status_code in (200, 201):
                    return True, f"GitHub:OK after conflict retry ({users} کاربر)"
                r = r2
        if r.status_code == 404:
            return False, "GitHub 404: Repository/Branch/Token اشتباه است یا Token دسترسی Contents ندارد"
        if r.status_code in (401, 403):
            return False, f"GitHub {r.status_code}: Token دسترسی نوشتن به Contents ندارد"
        return False, f"GitHub error {r.status_code}: {r.text[:240]}"
    except Exception as e:
        logger.error("github_upload: %s", e, exc_info=True)
        return False, str(e)
    finally:
        for candidate in (snap, compressed):
            try:
                candidate.unlink(missing_ok=True)
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
        if GITHUB_FILE.lower().endswith(".gz"):
            try:
                raw = gzip.decompress(raw)
            except OSError:
                return 0
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
        if GITHUB_FILE.lower().endswith(".gz"):
            try:
                raw = gzip.decompress(raw)
            except OSError:
                return False, "بکاپ GitHub فشرده خراب است"
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
    """Restore automatically from optional GitHub; Telegram backups require /restore."""
    global _LAST_RESTORE_STATUS
    local_n = _user_count(DB_PATH) if Path(DB_PATH).exists() else 0
    _LAST_RESTORE_STATUS = {"ok": False, "msg": "", "local_users": local_n, "remote_users": -1}
    if local_n == 0:
        attempts = []
        if github_enabled():
            ok, msg = github_download_db(); attempts.append(f"GitHub: {msg}")
            if ok:
                _LAST_RESTORE_STATUS.update({"ok": True, "msg": msg, "local_users": _user_count(DB_PATH)}); return True
        if telegram_backup_enabled():
            attempts.append("Telegram: بکاپ موجود است؛ برای ریستور فایل بکاپ را با /restore ارسال کن")
        _LAST_RESTORE_STATUS["msg"] = " | ".join(attempts) if attempts else "بکاپ ابری تنظیم نشده؛ Telegram را برای بکاپ فعال کن"
        return False
    try: remote_n = github_remote_user_count() if github_enabled() else 0
    except Exception: remote_n = 0
    _LAST_RESTORE_STATUS["remote_users"] = remote_n
    if remote_n > local_n:
        ok, msg = github_download_db()
        _LAST_RESTORE_STATUS.update({"ok": ok, "msg": msg, "local_users": _user_count(DB_PATH), "remote_users": remote_n}); return ok
    msg = f"DB OK — local={local_n} remote={remote_n}"
    logger.info(msg); _LAST_RESTORE_STATUS.update({"ok": True, "msg": msg, "local_users": local_n}); return False


def telegram_backup_enabled() -> bool:
    """Backup target: a private Telegram channel/group/chat."""
    return bool(os.getenv("TELEGRAM_BACKUP_CHAT_ID", "").strip() and config.BOT_TOKEN)


def _telegram_backup_chat_ids() -> list[int | str]:
    raw = os.getenv("TELEGRAM_BACKUP_CHAT_ID", "").strip()
    if not raw:
        return []
    result = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            result.append(int(item))
        except ValueError:
            result.append(item)
    return result


def auto_backup():
    """Local backup + Telegram off-site backup + optional GitHub."""
    results = []; local_ok = False
    try:
        backup_db(); stable = Path(DB_PATH).parent / "bot_data.backup.db"
        local_ok = bool(stable.exists() and _validate_sqlite_backup(stable)[0])
        results.append("local:OK" if local_ok else "local:FAIL(backup artifact missing/invalid)")
    except Exception as e:
        logger.error("local backup: %s", e, exc_info=True); results.append(f"local:FAIL({e})")
    # Telegram is the primary no-card off-site copy. The periodic Telegram job
    # sends a full SQLite snapshot; keeping the upload separate avoids duplicate files.
    results.append("telegram:configured" if telegram_backup_enabled() else "telegram:disabled")
    if github_enabled():
        try:
            ok, msg = github_upload_db(); results.append(f"github:{'OK' if ok else 'FAIL'}({msg})")
        except Exception as e:
            logger.error("github backup: %s", e, exc_info=True); results.append(f"github:FAIL({e})")
    else:
        results.append("github:disabled")
    return bool(local_ok or telegram_backup_enabled()), " | ".join(results)

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
        recipients = list(config.ADMIN_IDS)
        for backup_chat_id in _telegram_backup_chat_ids():
            if backup_chat_id not in recipients:
                recipients.append(backup_chat_id)
        for admin_id in recipients:
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

    msg = f"ارسال sync به {ok}/{len(set(config.ADMIN_IDS) | set(map(str, _telegram_backup_chat_ids())))} مقصد"
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

    # Telegram backup is sent below.

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
        recipients = list(config.ADMIN_IDS)
        for backup_chat_id in _telegram_backup_chat_ids():
            if backup_chat_id not in recipients:
                recipients.append(backup_chat_id)
        for admin_id in recipients:
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
    return ok > 0, f"ارسال به {ok} مقصد ({users} کاربر)"


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
    text = (
        "⚠️ دیتابیس بعد از استارت هنوز خالی است.\n\n"
        f"نتیجه ریستور خودکار:\n{detail}\n\n"
        "کار لازم:\n"
        "۱) از کانال/چت خصوصی بکاپ، آخرین فایل .db را بردار و با کپشن /restore بفرست\n"
        "۲) اگر GitHub فعال است، GITHUB_TOKEN و GITHUB_REPO را بررسی کن\n"
        "۳) بعد از ریستور موفق، /backup بزن تا یک نسخه جدید در Telegram ذخیره شود"
    )
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(chat_id=admin_id, text=text)
            await asyncio.sleep(0.2)
        except Exception as e:
            logger.error(f"notify empty: {e}")
