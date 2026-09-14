# Auto-split part 4: check_user_reminders
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
