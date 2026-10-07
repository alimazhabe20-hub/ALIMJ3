"""database: stats responsibilities."""
from .database_common import *  # noqa: F401,F403
from . import database_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


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

def add_note(user_id, content):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO notes (user_id, content) VALUES (?, ?)", (user_id, content[:500]))
    conn.commit()
    conn.close()

def get_notes(user_id, limit=10):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, content, created_at FROM notes WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit))
    rows = c.fetchall()
    conn.close()
    return rows

def delete_note(user_id, note_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM notes WHERE id = ? AND user_id = ?", (note_id, user_id))
    conn.commit()
    conn.close()

def track_usage(user_id, feature):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''INSERT INTO usage_stats (user_id, feature, count, last_used)
                 VALUES (?, ?, 1, datetime('now'))
                 ON CONFLICT(user_id, feature) DO UPDATE SET
                 count = count + 1, last_used = datetime('now')''', (user_id, feature))
    conn.commit()
    conn.close()

def get_user_usage(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT feature, count FROM usage_stats WHERE user_id = ? ORDER BY count DESC", (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_automation_preferences(user_id):
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT daily_digest, last_digest_date FROM automation_preferences WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if not row:
            return {"daily_digest": False, "last_digest_date": None}
        return {"daily_digest": bool(row[0]), "last_digest_date": row[1]}
    finally:
        conn.close()

def set_daily_digest(user_id, enabled):
    enabled = 1 if enabled else 0
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO automation_preferences (user_id, daily_digest, updated_at) "
            "VALUES (?, ?, datetime('now')) "
            "ON CONFLICT(user_id) DO UPDATE SET daily_digest=excluded.daily_digest, updated_at=datetime('now')",
            (user_id, enabled),
        )
        conn.commit()
    finally:
        conn.close()

def get_users_for_daily_digest(date_key, limit=5000):
    conn = get_db_connection()
    try:
        return conn.execute(
            "SELECT user_id FROM automation_preferences "
            "WHERE daily_digest = 1 AND COALESCE(last_digest_date, '') <> ? LIMIT ?",
            (date_key, max(1, int(limit))),
        ).fetchall()
    finally:
        conn.close()

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

def get_upcoming_user_reminders(user_id, now_iso, limit=5):
    conn = get_db_connection()
    try:
        return conn.execute(
            "SELECT text, remind_at, COALESCE(repeat_type,'once') FROM reminders "
            "WHERE user_id = ? AND done = 0 AND COALESCE(active,1) = 1 AND remind_at >= ? "
            "ORDER BY remind_at ASC LIMIT ?",
            (user_id, now_iso, max(1, int(limit))),
        ).fetchall()
    finally:
        conn.close()
