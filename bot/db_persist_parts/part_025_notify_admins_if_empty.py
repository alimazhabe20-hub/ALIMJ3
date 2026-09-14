# Auto-split part 25: notify_admins_if_empty
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
