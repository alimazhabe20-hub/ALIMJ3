# Auto-split part 47: get_top_user_features
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
