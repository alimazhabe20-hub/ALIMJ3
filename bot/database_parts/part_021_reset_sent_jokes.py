# Auto-split part 21: reset_sent_jokes
def reset_sent_jokes(user_id):
    """اگر همه جوک‌ها دیده شد، تاریخچه را پاک کن تا از اول شروع شود"""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("DELETE FROM sent_jokes WHERE user_id = ?", (user_id,))
        conn.commit()
    except Exception as e:
        logger.error(f"reset_sent_jokes: {e}")
    finally:
        conn.close()
