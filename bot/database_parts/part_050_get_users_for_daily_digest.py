# Auto-split part 50: get_users_for_daily_digest
def get_users_for_daily_digest(date_key, limit=5000):
    conn = get_db_connection()
    try:
        return conn.execute(
            "SELECT user_id FROM automation_preferences "
            "WHERE daily_digest = 1 AND COALESCE(last_digest_date, '') <> ? LIMIT ?",
            (date_key, max(1, int(limit))),
        ).fetchall()
    finally:
        conn.close()
