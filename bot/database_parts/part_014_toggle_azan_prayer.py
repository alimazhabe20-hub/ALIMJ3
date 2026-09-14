# Auto-split part 14: toggle_azan_prayer
def toggle_azan_prayer(user_id, prayer_key: str) -> bool:
    """
    روشن/خاموش کردن یک اذان خاص.
    prayer_key: fajr|dhuhr|asr|maghrib|isha
    برمی‌گرداند وضعیت جدید (True=روشن)
    """
    if prayer_key not in AZAN_FIELDS:
        return False
    field, _ = AZAN_FIELDS[prayer_key]
    settings = get_azan_settings(user_id)
    new_val = not settings.get(prayer_key, False)
    update_user_field(user_id, field, 1 if new_val else 0)
    return new_val
