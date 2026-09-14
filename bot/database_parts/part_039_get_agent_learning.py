# Auto-split part 39: get_agent_learning
def get_agent_learning(user_id, limit=50):
    """Return recent agent learning rows for diagnostics/UI."""
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT agent, tool, success_count, failure_count, last_error, updated_at "
            "FROM agent_learning WHERE user_id = ? ORDER BY updated_at DESC LIMIT ?",
            (user_id, max(1, min(int(limit), 100))),
        ).fetchall()
        return rows
    finally:
        conn.close()
