async def _show_azan_settings(update, user_id, city, note: str = None):
    """نمایش پنل تنظیم اذان با وضعیت فعلی و اوقات شرعی"""
    from bot.api.prayer import get_prayer_times, get_next_prayer_time
    from datetime import datetime
    import pytz
    from bot.config import config
    settings = get_azan_settings(user_id)
    times = get_prayer_times(city) or {}
    now = datetime.now(pytz.timezone(config.TIMEZONE))
    nxt_name, nxt_delta = get_next_prayer_time(times, now) if times else (None, None)
    def mark(on: bool) -> str:
        return "✅" if on else "❌"
    lines = [f"🔔 تنظیم اذان — {city}\n"]
    if note:
        lines.append(f"ℹ️ {note}\n")
    master = "روشن ✅" if settings["enabled"] else "خاموش ❌"
    lines.append(f"اعلان کلی: {master}\n")
    lines.append("انتخاب اذان‌ها:")
    lines.append(f"{mark(settings['fajr'])} اذان صبح" + (f"  ({times.get('اذان صبح', '—')})" if times else ""))
    lines.append(f"{mark(settings['dhuhr'])} اذان ظهر" + (f"  ({times.get('اذان ظهر', '—')})" if times else ""))
    lines.append(f"{mark(settings['asr'])} اذان عصر" + (f"  ({times.get('اذان عصر', '—')})" if times else ""))
    lines.append(f"{mark(settings['maghrib'])} اذان مغرب" + (f"  ({times.get('اذان مغرب', '—')})" if times else ""))
    lines.append(f"{mark(settings['isha'])} اذان عشاء" + (f"  ({times.get('اذان عشاء', '—')})" if times else ""))
    if nxt_name and nxt_delta and settings["enabled"]:
        secs = int(nxt_delta.total_seconds())
        h, r = divmod(secs, 3600)
        mi, _ = divmod(r, 60)
        lines.append(f"\n⏳ اذان بعدی: {nxt_name} — {h} ساعت و {mi} دقیقه")
    elif not settings["enabled"]:
        lines.append("\n🔕 اعلان‌ها خاموش است.")
    lines.append("\nروی هر دکمه بزن تا روشن/خاموش شود.")
    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=get_azan_keyboard(settings),
    )
