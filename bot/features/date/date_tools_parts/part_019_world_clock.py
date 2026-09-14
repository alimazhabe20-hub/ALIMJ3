# Auto-split part 19: world_clock
def world_clock() -> str:
    now_utc = datetime.now(pytz.UTC)
    lines = ["🌍 **ساعت جهانی**\n"]
    for name, tz_name in WORLD_CITIES.items():
        tz = pytz.timezone(tz_name)
        local = now_utc.astimezone(tz)
        lines.append(f"• {name}: {local.strftime('%H:%M')} ({local.strftime('%d/%m')})")
    return "\n".join(lines)
