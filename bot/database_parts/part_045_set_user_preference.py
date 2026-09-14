# Auto-split part 45: set_user_preference
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
