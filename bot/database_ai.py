"""database: ai responsibilities."""
from .database_common import *  # noqa: F401,F403
from . import database_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


def set_ai_memory(user_id, key, value):
    key = (key or "note").strip()[:80]
    value = (value or "").strip()[:1000]
    if not value:
        return
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO ai_memory (user_id, key, value, updated_at) VALUES (?, ?, ?, datetime('now')) "
        "ON CONFLICT(user_id, key) DO UPDATE SET value = excluded.value, updated_at = datetime('now')",
        (user_id, key, value),
    )
    conn.commit()
    conn.close()

def get_ai_memory(user_id, limit=40, query=None):
    """Return memory, optionally ranked by lightweight lexical relevance.

    The original (key, value) return shape is preserved. Ranking is performed
    in Python to avoid DB-specific full-text dependencies and to keep upgrades
    backward compatible.
    """
    conn = get_db_connection()
    c = conn.cursor()
    try:
        # Read a bounded candidate set; this table is intentionally small.
        c.execute(
            "SELECT key, value, updated_at FROM ai_memory WHERE user_id = ? "
            "ORDER BY updated_at DESC LIMIT ?",
            (user_id, max(1, min(int(limit) * 3, 120))),
        )
        rows = c.fetchall()
    except Exception:
        return []
    finally:
        conn.close()

    if not query:
        return [(r[0], r[1]) for r in rows[:limit]]

    import re
    tokens = set(re.findall(r"[\w\u0600-\u06ff]{2,}", str(query).lower()))
    if not tokens:
        return [(r[0], r[1]) for r in rows[:limit]]

    scored = []
    for key, value, updated_at in rows:
        hay = f"{key} {value}".lower()
        overlap = sum(1 for token in tokens if token in hay)
        key_bonus = sum(2 for token in tokens if token in str(key).lower())
        score = overlap + key_bonus
        # Small recency tie-break without depending on timestamp parsing.
        scored.append((score, str(updated_at or ""), key, value))
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [(key, value) for score, _updated, key, value in scored[:limit]]

def delete_ai_memory(user_id, key=None):
    conn = get_db_connection()
    c = conn.cursor()
    if key:
        c.execute("DELETE FROM ai_memory WHERE user_id = ? AND key = ?", (user_id, key))
    else:
        c.execute("DELETE FROM ai_memory WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_ai_history_summary(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT summary FROM ai_history_summary WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        return row[0] if row and row[0] else ""
    except Exception:
        return ""
    finally:
        conn.close()

def set_ai_history_summary(user_id, summary):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO ai_history_summary (user_id, summary, updated_at) VALUES (?, ?, datetime('now')) "
        "ON CONFLICT(user_id) DO UPDATE SET summary = excluded.summary, updated_at = datetime('now')",
        (user_id, (summary or "")[:4000]),
    )
    conn.commit()
    conn.close()

def clear_ai_history_summary(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("DELETE FROM ai_history_summary WHERE user_id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()

def get_ai_preference(user_id):
    """Returns (provider, model) or None. model='*' means all models of provider."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute(
            "SELECT provider, model FROM ai_preferences WHERE user_id = ?",
            (user_id,),
        )
        row = c.fetchone()
        if row:
            return (row[0], row[1] or "*")
        return None
    except Exception:
        return None
    finally:
        conn.close()

def set_ai_preference(user_id, provider, model="*"):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO ai_preferences (user_id, provider, model, updated_at) "
            "VALUES (?, ?, ?, datetime('now')) "
            "ON CONFLICT(user_id) DO UPDATE SET "
            "provider = excluded.provider, model = excluded.model, "
            "updated_at = datetime('now')",
            (user_id, provider, model or "*"),
        )
        conn.commit()
    finally:
        conn.close()

def clear_ai_preference(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("DELETE FROM ai_preferences WHERE user_id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()

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
