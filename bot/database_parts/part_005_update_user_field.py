from typing import Any

# Auto-split part 5: update_user_field
def update_user_field(user_id: int, field: str, value: Any) -> None:
    allowed_fields = {
        "city", "country", "language", "subscribed",
        "notification_enabled", "notify_fajr", "notify_dhuhr",
        "notify_asr", "notify_maghrib", "notify_isha"
    }
    if field not in allowed_fields:
        logger.warning(f"Attempt to update invalid field: {field}")
        return
    _execute_write(
        f"UPDATE users SET {field} = ?, last_active = datetime('now') WHERE user_id = ?",
        (value, user_id),
    )
