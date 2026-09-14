# Auto-split part 38: get_agent_tool_reliability
def get_agent_tool_reliability(user_id, agent, tool):
    """Return (score, attempts, failures) with a neutral prior for unknown tools."""
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT success_count, failure_count FROM agent_learning WHERE user_id = ? AND agent = ? AND tool = ?",
            (user_id, str(agent or "general")[:40], str(tool or "unknown")[:80]),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return 0.5, 0, 0
    success, failures = int(row[0] or 0), int(row[1] or 0)
    attempts = success + failures
    return ((success / attempts) if attempts else 0.5), attempts, failures
