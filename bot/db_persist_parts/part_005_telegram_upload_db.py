# Auto-split part 5: telegram_upload_db
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
