"""db_persist: telegram responsibilities."""
from .db_persist_common import *  # noqa: F401,F403
from . import db_persist_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


def _telegram_backup_chat_ids() -> list[str]:
    """Return configured Telegram backup chat IDs, accepting comma/newline separated values."""
    raw = os.getenv("TELEGRAM_BACKUP_CHAT_ID", "").strip()
    return [item.strip() for item in re.split(r"[,\n;]+", raw) if item.strip()]

def telegram_backup_enabled() -> bool:
    return bool(config.BOT_TOKEN and _telegram_backup_chat_ids())

def _telegram_api(method: str, **kwargs):
    url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/{method}"
    return requests.post(url, timeout=max(REMOTE_BACKUP_TIMEOUT, 30), **kwargs)

def _telegram_get(method: str, **kwargs):
    url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/{method}"
    return requests.get(url, timeout=max(REMOTE_BACKUP_TIMEOUT, 30), **kwargs)

def telegram_upload_db() -> tuple[bool, str]:
    """Upload a fresh SQLite snapshot to configured Telegram targets and pin it.

    The pinned message is the only Bot-API-compatible pointer that survives a
    local DB loss.  We verify the pin immediately so a successful HTTP upload
    can never be mistaken for a usable automatic-restore backup.
    """
    if not telegram_backup_enabled():
        return False, "Telegram backup تنظیم نشده (TELEGRAM_BACKUP_CHAT_ID)"
    chat_ids = _telegram_backup_chat_ids()
    if not chat_ids:
        return False, "TELEGRAM_BACKUP_CHAT_ID نامعتبر است"
    users = _user_count(DB_PATH)
    if users == 0:
        return False, "DB خالی است — Telegram آپلود نشد"
    snap = _sqlite_snapshot_to_temp()
    if not snap:
        return False, "اسنپ‌شات SQLite ساخته نشد"
    successes = 0
    details = []
    try:
        size = snap.stat().st_size
        if size > 50 * 1024 * 1024:
            return False, f"بکاپ {size//(1024*1024)}MB است و از سقف ارسال Bot API بیشتر است"
        for chat_id in chat_ids:
            try:
                caption = (
                    "💾 بکاپ خودکار دیتابیس\n"
                    f"👥 کاربران: {users}\n"
                    f"📦 {size/1024:.1f} KB\n"
                    f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                    "🔐 آخرین بکاپ خودکار — پیام را حذف نکنید"
                )
                with open(snap, "rb") as f:
                    r = _telegram_api(
                        "sendDocument",
                        data={"chat_id": chat_id, "caption": caption},
                        files={"document": (f"bot_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db", f)},
                    )
                data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
                if r.status_code != 200 or not data.get("ok"):
                    details.append(f"{chat_id}:sendDocument {r.status_code} {r.text[:120]}")
                    continue
                message_id = (data.get("result") or {}).get("message_id")
                if not message_id:
                    details.append(f"{chat_id}:message_id نامشخص")
                    continue
                pin = _telegram_api(
                    "pinChatMessage",
                    data={"chat_id": chat_id, "message_id": message_id, "disable_notification": True},
                )
                pin_data = pin.json() if pin.headers.get("content-type", "").startswith("application/json") else {}
                if pin.status_code != 200 or not pin_data.get("ok"):
                    details.append(f"{chat_id}:ارسال شد ولی PIN نشد ({pin.status_code})")
                    continue

                # Verify the pointer immediately. If this fails, automatic restore
                # on a fresh instance would not be reliable.
                verified = False
                verify_error = ""
                for attempt in range(1, 4):
                    try:
                        chk = _telegram_get("getChat", params={"chat_id": chat_id})
                        chk_data = chk.json() if chk.headers.get("content-type", "").startswith("application/json") else {}
                        pinned = (chk_data.get("result") or {}).get("pinned_message") or {}
                        if chk.status_code == 200 and chk_data.get("ok") and int(pinned.get("message_id") or 0) == int(message_id):
                            verified = True
                            break
                        verify_error = f"getChat={chk.status_code}, pinned_message_id={pinned.get('message_id')}"
                    except Exception as exc:
                        verify_error = str(exc)
                    if attempt < 3:
                        time.sleep(0.7 * attempt)
                if verified:
                    successes += 1
                    details.append(f"{chat_id}:OK (پیام {message_id} پین و تأیید شد)")
                    logger.info("Telegram channel backup OK (%s users, chat=%s, message_id=%s)", users, chat_id, message_id)
                else:
                    details.append(f"{chat_id}:PIN تأیید نشد ({verify_error})")
            except Exception as exc:
                details.append(f"{chat_id}:{exc}")
                logger.error("telegram_upload_db target %s: %s", chat_id, exc, exc_info=True)
        if successes:
            return True, f"Telegram:OK — {successes}/{len(chat_ids)} مقصد | " + " ; ".join(details)
        return False, "Telegram: ارسال/Pin موفق نبود | " + " ; ".join(details)
    finally:
        try:
            snap.unlink(missing_ok=True)
        except Exception:
            pass

def telegram_download_pinned_db() -> tuple[bool, str]:
    """Automatically restore the verified pinned backup from Telegram."""
    if not telegram_backup_enabled():
        return False, "Telegram backup تنظیم نشده"
    chat_ids = _telegram_backup_chat_ids()
    if not chat_ids:
        return False, "TELEGRAM_BACKUP_CHAT_ID نامعتبر است"
    diagnostics = []
    for chat_id in chat_ids:
        try:
            # Telegram may briefly lag after deploy/restart, so retry the pointer lookup.
            data = {}
            pinned = {}
            last_status = 0
            for attempt in range(1, 4):
                r = _telegram_get("getChat", params={"chat_id": chat_id})
                last_status = r.status_code
                data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
                if r.status_code == 200 and data.get("ok"):
                    pinned = (data.get("result") or {}).get("pinned_message") or {}
                    if pinned:
                        break
                if attempt < 3:
                    time.sleep(0.8 * attempt)
            if last_status != 200 or not data.get("ok"):
                diagnostics.append(f"{chat_id}:getChat={last_status} — ربات/شناسه کانال را بررسی کن")
                continue
            if not pinned:
                diagnostics.append(f"{chat_id}:PIN پیدا نشد — باید یک بکاپ توسط ربات ارسال و Pin شده باشد")
                continue

            document = pinned.get("document") or {}
            file_id = document.get("file_id")
            if not file_id:
                diagnostics.append(f"{chat_id}:پیام پین‌شده فایل DB نیست (message_id={pinned.get('message_id')})")
                continue
            file_size = int(document.get("file_size") or 0)
            if file_size > TELEGRAM_BACKUP_MAX_DOWNLOAD_BYTES:
                diagnostics.append(f"{chat_id}:حجم بکاپ بیش از حد مجاز است")
                continue
            gf = _telegram_get("getFile", params={"file_id": file_id})
            gf_data = gf.json() if gf.headers.get("content-type", "").startswith("application/json") else {}
            if gf.status_code != 200 or not gf_data.get("ok"):
                diagnostics.append(f"{chat_id}:getFile={gf.status_code} {gf.text[:120]}")
                continue
            file_path = (gf_data.get("result") or {}).get("file_path")
            if not file_path:
                diagnostics.append(f"{chat_id}:file_path دریافت نشد")
                continue
            dl_url = f"https://api.telegram.org/file/bot{config.BOT_TOKEN}/{file_path}"
            dl = requests.get(dl_url, timeout=max(REMOTE_BACKUP_TIMEOUT, 45))
            if dl.status_code != 200:
                diagnostics.append(f"{chat_id}:download={dl.status_code}")
                continue
            raw = dl.content
            if len(raw) > TELEGRAM_BACKUP_MAX_DOWNLOAD_BYTES:
                diagnostics.append(f"{chat_id}:فایل دانلودشده بزرگ‌تر از حد مجاز است")
                continue
            tmp = Path(DB_PATH).with_suffix(f".db.telegram.{secrets.token_hex(4)}")
            try:
                tmp.write_bytes(raw)
                valid, count_or_error = _validate_sqlite_backup(tmp)
                if not valid or int(count_or_error) <= 0:
                    diagnostics.append(f"{chat_id}:بکاپ نامعتبر — {count_or_error}")
                    continue
                n = int(count_or_error)
                dest = Path(DB_PATH)
                dest.parent.mkdir(parents=True, exist_ok=True)
                if dest.exists() and _user_count(dest) > 0:
                    try:
                        backup_db()
                    except Exception:
                        logger.warning("pre-Telegram-restore local backup failed", exc_info=True)
                source = sqlite3.connect(str(tmp), timeout=30)
                target = sqlite3.connect(str(dest), timeout=30)
                try:
                    target.execute("PRAGMA busy_timeout=30000")
                    source.backup(target)
                    target.commit()
                finally:
                    target.close()
                    source.close()
                logger.warning("Restored from pinned Telegram backup — %s users (chat=%s)", n, chat_id)
                return True, f"از بکاپ پین‌شده Telegram بازگردانی شد — {n} کاربر (chat={chat_id})"
            finally:
                tmp.unlink(missing_ok=True)
        except Exception as exc:
            logger.error("telegram_download_pinned_db %s: %s", chat_id, exc, exc_info=True)
            diagnostics.append(f"{chat_id}:خطا — {exc}")
    return False, " | ".join(diagnostics) if diagnostics else "هیچ مقصد Telegram قابل بررسی نیست"
