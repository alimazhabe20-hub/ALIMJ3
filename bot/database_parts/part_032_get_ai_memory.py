# Auto-split part 32: get_ai_memory
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
