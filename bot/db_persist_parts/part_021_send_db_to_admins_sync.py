# Auto-split part 21: send_db_to_admins_sync
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
