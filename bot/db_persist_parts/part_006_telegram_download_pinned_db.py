# Auto-split part 6: telegram_download_pinned_db
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
