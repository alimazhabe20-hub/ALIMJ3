# Auto-split part 51: mark_daily_digest_sent
def mark_daily_digest_sent(user_id, date_key):
    conn = get_db_connection()
    try:
        cur = conn.execute(
            "UPDATE automation_preferences SET last_digest_date = ?, updated_at = datetime('now') "
            "WHERE user_id = ? AND daily_digest = 1 AND COALESCE(last_digest_date, '') <> ?",
            (date_key, user_id, date_key),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()
