# Auto-split part 4: save_user
def save_user(user_id: int, first_name: str | None, city: str = "قم", country: str = "Iran", language: str = "fa") -> None:
    """ثبت/به‌روزرسانی کاربر با retry محدود در صورت lock دیتابیس."""
    _execute_write(
        "INSERT INTO users "
        "(user_id, first_name, city, country, language, subscribed, "
        "register_date, last_active, notification_enabled, notify_fajr, "
        "notify_dhuhr, notify_asr, notify_maghrib, notify_isha) "
        "VALUES (?, ?, ?, ?, ?, 1, datetime('now'), datetime('now'), 0, 0, 0, 0, 0, 0) "
        "ON CONFLICT(user_id) DO UPDATE SET "
        "first_name=excluded.first_name, last_active=datetime('now')",
        (user_id, first_name, city, country, language),
    )
