# Auto-split part 12: setup_scheduler
def setup_scheduler(app):
    job_queue = app.job_queue
    if not job_queue:
        logger.error("JobQueue not available! Scheduler disabled.")
        return

    tehran = pytz.timezone(config.TIMEZONE)

    job_queue.run_daily(
        send_daily_messages,
        time=time(hour=0, minute=0, second=0, tzinfo=tehran),
        name="daily_broadcast",
    )

    async def _job_update_stats(context):
        # update_stats is sync; JobQueue in PTB v20 awaits the callback.
        try:
            update_stats()
        except Exception as exc:
            logger.error("daily_stats job failed: %s", exc, exc_info=True)

    job_queue.run_daily(
        _job_update_stats,
        time=time(hour=23, minute=59, second=0, tzinfo=tehran),
        name="daily_stats",
    )
    job_queue.run_repeating(
        check_azan_notifications,
        interval=60,
        first=10,
        name="azan_timer",
    )
    # یادآوری‌های کاربر هر ۳۰ ثانیه
    job_queue.run_repeating(
        check_user_reminders,
        interval=30,
        first=15,
        name="user_reminders",
    )
    job_queue.run_repeating(
        check_economic_calendar_alerts,
        interval=60,
        first=25,
        name="economic_calendar_alerts",
    )
    job_queue.run_repeating(check_v65_price_alerts, interval=60, first=40, name="v65_price_alerts")
    job_queue.run_repeating(v71_due_jobs, interval=30, first=45, name="v71_scheduled_ai")
    # بکاپ پرتکرار: local + Cloudflare R2 (+ GitHub fallback). فاصله از env قابل تنظیم است (پیش‌فرض ۳۰ دقیقه).
    job_queue.run_repeating(
        periodic_backup,
        interval=getattr(config, "BACKUP_INTERVAL_SECONDS", 1800),
        first=120,
        name="db_backup_remote",
    )
    # ارسال کپی اضطراری برای ادمین‌ها با فاصله طولانی‌تر (پیش‌فرض ۶ ساعت).
    job_queue.run_repeating(
        periodic_telegram_backup,
        interval=getattr(config, "TELEGRAM_BACKUP_INTERVAL_SECONDS", 21600),
        first=300,
        name="db_backup_telegram",
    )
    if getattr(config, "UPDATE_MANIFEST_URL", ""):
        job_queue.run_repeating(
            check_update_center,
            interval=max(3600, int(getattr(config, "UPDATE_CHECK_TTL", 1800)) * 12),
            first=600,
            name="update_center_check",
        )
    # Opt-in proactive digest; disabled for users by default.
    from bot.automation import send_daily_digests
    digest_hour = max(0, min(23, int(getattr(config, "AUTOMATION_DIGEST_HOUR", 8))))
    job_queue.run_daily(
        send_daily_digests,
        time=time(hour=digest_hour, minute=0, second=0, tzinfo=tehran),
        name="proactive_daily_digest",
    )
    logger.info("Scheduler ready: daily + azan + reminders + proactive digest + remote backup + Telegram backup")
