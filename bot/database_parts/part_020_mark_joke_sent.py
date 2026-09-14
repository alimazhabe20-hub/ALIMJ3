# Auto-split part 20: mark_joke_sent
def mark_joke_sent(user_id, joke_hash):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute(
            "INSERT OR IGNORE INTO sent_jokes (user_id, joke_hash) VALUES (?, ?)",
            (user_id, joke_hash),
        )
        conn.commit()
    except Exception as e:
        logger.error(f"mark_joke_sent: {e}")
    finally:
        conn.close()
