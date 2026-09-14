# Auto-split part 2: check_azan_notifications
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
