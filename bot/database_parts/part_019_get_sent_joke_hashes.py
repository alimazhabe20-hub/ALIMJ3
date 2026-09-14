# Auto-split part 19: get_sent_joke_hashes
def get_sent_joke_hashes(user_id, limit=5000):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute(
            "SELECT joke_hash FROM sent_jokes WHERE user_id = ? ORDER BY sent_at DESC LIMIT ?",
            (user_id, limit),
        )
        return {row[0] for row in c.fetchall()}
    except Exception:
        return set()
    finally:
        conn.close()
