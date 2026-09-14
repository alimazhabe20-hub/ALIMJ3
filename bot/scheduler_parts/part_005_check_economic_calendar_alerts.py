# Auto-split part 5: check_economic_calendar_alerts
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
