"""database: users responsibilities."""
from .database_common import *  # noqa: F401,F403
from . import database_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


def get_user(user_id: int) -> tuple[Any, ...] | None:
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result

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

def get_all_users() -> list[tuple[Any, ...]]:
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT user_id, first_name, city, language FROM users WHERE subscribed = 1")
    result = c.fetchall()
    conn.close()
    return result

def get_active_users_today() -> int:
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users WHERE date(last_active) = date('now')")
    result = c.fetchone()[0]
    conn.close()
    return result

def update_stats() -> None:
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total = c.fetchone()[0]
    active = get_active_users_today()
    c.execute("INSERT INTO stats (date, total_users, active_users) VALUES (date('now'), ?, ?)", (total, active))
    conn.commit()
    conn.close()
    logger.info(f"Stats updated: total={total}, active={active}")

def get_user_city(user_id: int) -> str:
    user = get_user(user_id)
    return user[2] if user else "قم"

def get_user_country(user_id: int) -> str:
    user = get_user(user_id)
    return user[3] if user else "Iran"

def get_user_language(user_id: int) -> str:
    user = get_user(user_id)
    return user[4] if user else "fa"

def get_user_preferences(user_id):
    """Return lightweight UX preferences without exposing raw conversation data."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute(
            "SELECT response_style, currency FROM user_preferences WHERE user_id = ?",
            (user_id,),
        )
        row = c.fetchone()
        if not row:
            return {"response_style": "balanced", "currency": "USD"}
        return {"response_style": row[0] or "balanced", "currency": row[1] or "USD"}
    finally:
        conn.close()

def set_user_preference(user_id, key, value):
    """Safely update one supported UX preference."""
    allowed = {"response_style", "currency"}
    if key not in allowed:
        raise ValueError("unsupported preference")
    value = str(value).strip()[:32]
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO user_preferences (user_id, response_style, currency, updated_at) "
            "VALUES (?, ?, ?, datetime('now')) "
            "ON CONFLICT(user_id) DO UPDATE SET "
            f"{key} = excluded.{key}, updated_at = datetime('now')",
            (user_id, value if key == "response_style" else "balanced",
             value if key == "currency" else "USD"),
        )
        conn.commit()
    finally:
        conn.close()

def clear_user_preferences(user_id):
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM user_preferences WHERE user_id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()

def get_top_user_features(user_id, limit=3):
    """Return most-used features, preferring recent usage when counts tie."""
    limit = max(1, min(int(limit), 10))
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT feature, count FROM usage_stats WHERE user_id = ? "
            "ORDER BY count DESC, last_used DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return rows
    finally:
        conn.close()

def set_birth_date(user_id, birth_date):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET birth_date = ? WHERE user_id = ?", (birth_date, user_id))
    conn.commit()
    conn.close()

def get_birth_date(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT birth_date FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        return row[0] if row else None
    except Exception:
        return None
    finally:
        conn.close()

def get_last_main_msg_id(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT last_main_msg_id FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        return row[0] if row else None
    except Exception:
        return None
    finally:
        conn.close()

def set_last_main_msg_id(user_id, message_id):
    try:
        _execute_write("UPDATE users SET last_main_msg_id = ? WHERE user_id = ?", (message_id, user_id))
    except Exception as e:
        logger.error(f"set_last_main_msg_id failed: {e}")
