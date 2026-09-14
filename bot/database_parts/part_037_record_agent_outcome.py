# Auto-split part 37: record_agent_outcome
def record_agent_outcome(user_id, agent, tool, success, error=""):
    """Record bounded agent/tool feedback for future routing decisions."""
    agent = (str(agent or "general").strip()[:40] or "general")
    tool = (str(tool or "unknown").strip()[:80] or "unknown")
    error = str(error or "").strip()[:500]
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO agent_learning "
            "(user_id, agent, tool, success_count, failure_count, last_success, last_failure, last_error, updated_at) "
            "VALUES (?, ?, ?, ?, ?, CASE WHEN ? THEN datetime('now') ELSE NULL END, "
            "CASE WHEN ? THEN datetime('now') ELSE NULL END, ?, datetime('now')) "
            "ON CONFLICT(user_id, agent, tool) DO UPDATE SET "
            "success_count = success_count + excluded.success_count, "
            "failure_count = failure_count + excluded.failure_count, "
            "last_success = CASE WHEN excluded.success_count > 0 THEN datetime('now') ELSE agent_learning.last_success END, "
            "last_failure = CASE WHEN excluded.failure_count > 0 THEN datetime('now') ELSE agent_learning.last_failure END, "
            "last_error = CASE WHEN excluded.failure_count > 0 THEN excluded.last_error ELSE agent_learning.last_error END, "
            "updated_at = datetime('now')",
            (user_id, agent, tool, int(bool(success)), int(not success), bool(success), bool(not success), error),
        )
        conn.commit()
    finally:
        conn.close()
