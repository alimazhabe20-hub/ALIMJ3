from datetime import time, datetime, timedelta
import pytz
from bot.logger import logger
from bot.database import (
    get_all_users,
    update_stats,
    get_users_for_azan,
    backup_db,
    get_pending_reminders,
    mark_reminder_done,
    reschedule_reminder,
    get_economic_calendar_alert_users, economic_calendar_alert_was_sent, mark_economic_calendar_alert_sent,
)
from bot.utils.helpers import build_message, get_refresh_button
from bot.config import config
from bot.api.prayer import get_prayer_times
from bot.db_persist import send_db_to_admins
import asyncio

PRAYER_FLAGS = {
    "اذان صبح": 3,
    "اذان ظهر": 4,
    "اذان عصر": 5,
    "اذان مغرب": 6,
    "اذان عشاء": 7,
}


async def send_daily_messages(context):
    logger.info("Starting daily broadcast...")
    users = get_all_users()
    count = 0
    for user_id, first_name, city, lang in users:
        try:
            msg = await build_message(user_id, first_name, city)
            await context.bot.send_message(
                chat_id=user_id,
                text=msg,
                reply_markup=get_refresh_button()
            )
            count += 1
            await asyncio.sleep(0.2)
        except Exception as e:
            logger.error(f"Failed to send to {user_id}: {e}")
    logger.info(f"Daily broadcast sent to {count}/{len(users)} users")


async def check_azan_notifications(context):
    tehran = pytz.timezone(config.TIMEZONE)
    now = datetime.now(tehran)
    users = get_users_for_azan()
    for row in users:
        try:
            user_id = row[0]
            city = row[1] if len(row) > 1 and row[1] else "تهران"
            times = get_prayer_times(city) or {}
            for prayer_name, flag_idx in PRAYER_FLAGS.items():
                if flag_idx >= len(row) or not row[flag_idx]:
                    continue
                tstr = times.get(prayer_name)
                if not tstr:
                    continue
                try:
                    hh, mm = map(int, tstr.split(":")[:2])
                except Exception:
                    continue
                target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
                diff = (target - now).total_seconds()
                if 0 <= diff < 60:
                    text = (
                        f"🔔 {prayer_name}\n"
                        f"شهر: {city}\n"
                        f"ساعت: {tstr}\n\n"
                        f"الله اکبر"
                    )
                    await context.bot.send_message(chat_id=user_id, text=text)
                    await asyncio.sleep(0.05)
        except Exception as e:
            logger.error(f"azan notify error: {e}")


def _next_occurrence(when: datetime, repeat_type: str, repeat_every: int) -> datetime | None:
    """محاسبه زمان بعدی برای یادآوری تکراری."""
    rt = (repeat_type or "once").lower()
    if rt in ("once", "", "none"):
        return None
    if rt == "daily":
        return when + timedelta(days=max(1, repeat_every or 1))
    if rt == "weekly":
        return when + timedelta(weeks=max(1, repeat_every or 1))
    if rt == "monthly":
        # تقریبی ۳۰ روز
        return when + timedelta(days=30 * max(1, repeat_every or 1))
    if rt in ("every_minutes", "minutes", "minutely"):
        mins = max(1, int(repeat_every or 1))
        return when + timedelta(minutes=mins)
    if rt in ("every_hours", "hours", "hourly"):
        hrs = max(1, int(repeat_every or 1))
        return when + timedelta(hours=hrs)
    return None


async def check_user_reminders(context):
    """ارسال یادآوری‌های سررسید (یک‌بار و تکراری)."""
    tehran = pytz.timezone(config.TIMEZONE)
    now = datetime.now(tehran)
    now_iso = now.isoformat()
    try:
        rows = get_pending_reminders(before_time=now_iso)
    except Exception as e:
        logger.error(f"get_pending_reminders: {e}")
        return

    for row in rows:
        try:
            if len(row) >= 7:
                rid, user_id, text, remind_at, repeat_type, repeat_every, active = row[:7]
            else:
                rid, user_id, text, remind_at = row[:4]
                repeat_type, repeat_every, active = "once", 0, 1

            if not active:
                continue

            body = text or "یادآوری"
            msg = f"⏰ یادآوری\n\n{body}"
            if repeat_type and repeat_type not in ("once", "", "none"):
                msg += f"\n\n🔁 تکرار: {repeat_type}"
                if repeat_every:
                    msg += f" (هر {repeat_every})"

            await context.bot.send_message(chat_id=user_id, text=msg)

            # زمان پایه برای محاسبه بعدی
            try:
                base = datetime.fromisoformat(remind_at)
                if base.tzinfo is None:
                    base = tehran.localize(base)
            except Exception:
                base = now

            nxt = _next_occurrence(base, repeat_type, int(repeat_every or 0))
            # اگر از الان عقب‌تر شد، از الان جلو برو
            if nxt is not None:
                while nxt <= now:
                    nxt2 = _next_occurrence(nxt, repeat_type, int(repeat_every or 0))
                    if nxt2 is None or nxt2 <= nxt:
                        break
                    nxt = nxt2
                reschedule_reminder(rid, nxt.isoformat())
            else:
                mark_reminder_done(rid)

            await asyncio.sleep(0.05)
        except Exception as e:
            logger.error(f"reminder send error: {e}")



async def check_economic_calendar_alerts(context):
    """هشدار رویدادهای اقتصادی مهم، یک‌بار برای هر کاربر/رویداد."""
    try:
        from bot.features.market.economic_calendar import refresh_calendar, _tz, IMPACT_ICON, IMPACT_FA, format_value
        events = await refresh_calendar()
        now_utc = datetime.now(pytz.UTC)
    except Exception as e:
        logger.debug("economic calendar alert refresh failed: %s", e)
        return

    for row in get_economic_calendar_alert_users():
        try:
            user_id, lead_minutes, tz_name, currencies_raw, impact = row
            tz = _tz(tz_name or config.TIMEZONE)
            currencies = {x.strip().upper() for x in (currencies_raw or "").split(",") if x.strip()}
            max_delta = timedelta(minutes=max(1, int(lead_minutes or 15)))
            from bot.features.market.economic_calendar import MAJOR_CURRENCIES
            for e in events:
                # اگر کاربر ارز خاصی نگذاشته، فقط majors
                if currencies:
                    if e["country"] not in currencies:
                        continue
                elif e.get("country") not in MAJOR_CURRENCIES:
                    continue
                allowed = (impact or "high").lower()
                if allowed != "all":
                    if allowed == "medium":
                        if e["impact"].lower() not in {"high", "medium"}:
                            continue
                    elif e["impact"].lower() != allowed:
                        continue
                delta = e["utc"] - now_utc
                if delta.total_seconds() < 0 or delta > max_delta:
                    continue
                if economic_calendar_alert_was_sent(user_id, e["id"]):
                    continue
                local = e["utc"].astimezone(tz)
                mins = max(1, int(delta.total_seconds() // 60))
                text = (
                    f"🔔 هشدار تقویم اقتصادی\n\n"
                    f"{IMPACT_ICON.get(e['impact'], '⚪')} {e['title_fa']}\n"
                    f"💱 ارز: {e['country']} — {e['currency_name']}\n"
                    f"⏰ ساعت: {local.strftime('%H:%M')} ({tz.zone})\n"
                    f"⏳ حدود {mins} دقیقه مانده\n"
                    f"🚦 اهمیت: {IMPACT_FA.get(e['impact'], e['impact'])}\n\n"
                    f"🔮 پیش‌بینی: {format_value(e['forecast'])}\n"
                    f"◀️ قبلی: {format_value(e['previous'])}\n\n"
                    "🤖 برای تحلیل این خبر، از «تقویم اقتصادی» بخش بازار استفاده کن.\n"
                    "⚠️ هشدار آموزشی است و توصیه قطعی معامله نیست."
                )
                await context.bot.send_message(chat_id=user_id, text=text)
                mark_economic_calendar_alert_sent(user_id, e["id"])
                await asyncio.sleep(0.05)
        except Exception as e:
            logger.warning("economic calendar alert user failed: %s", e, exc_info=True)

async def periodic_backup(context):
    """بکاپ خودکار پرتکرار: local + GitHub؛ بدون اسپم تلگرام."""
    try:
        from bot.db_persist import auto_backup
        ok, msg = auto_backup()
        logger.info("auto_backup: %s", msg)
    except Exception as e:
        logger.error("periodic backup error: %s", e, exc_info=True)


async def periodic_telegram_backup(context):
    """یک کپی مستقل روی چت ادمین‌ها، با فاصله طولانی‌تر."""
    try:
        from bot.db_persist import send_db_to_admins, auto_backup
        ok, msg = auto_backup()
        ok2, msg2 = await send_db_to_admins(
            context.bot,
            caption=(
                "💾 بکاپ خودکار دوره‌ای\n"
                f"وضعیت: {msg}\n"
                f"🕐 {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}"
            ),
        )
        logger.info("telegram backup: %s", msg2)
    except Exception as e:
        logger.error("telegram periodic backup failed: %s", e, exc_info=True)


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
    # بکاپ پرتکرار: local + GitHub. فاصله از env قابل تنظیم است (پیش‌فرض ۳۰ دقیقه).
    job_queue.run_repeating(
        periodic_backup,
        interval=getattr(config, "BACKUP_INTERVAL_SECONDS", 1800),
        first=120,
        name="db_backup_remote",
    )
    # بکاپ Telegram با فاصله کمتر برای جلوگیری از اسپم (پیش‌فرض ۶ ساعت).
    job_queue.run_repeating(
        periodic_telegram_backup,
        interval=getattr(config, "TELEGRAM_BACKUP_INTERVAL_SECONDS", 21600),
        first=300,
        name="db_backup_telegram",
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
