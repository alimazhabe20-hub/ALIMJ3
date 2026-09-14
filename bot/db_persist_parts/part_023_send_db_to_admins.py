# Auto-split part 23: send_db_to_admins
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
