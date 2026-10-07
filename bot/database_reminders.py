"""database: reminders responsibilities."""
from .database_common import *  # noqa: F401,F403
from . import database_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


def add_reminder(user_id, text, remind_at, repeat_type="once", repeat_every=0):
    """
    repeat_type: once | daily | weekly | monthly | every_minutes
    repeat_every: برای every_minutes = تعداد دقیقه؛ برای بقیه معمولاً ۱
    """
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO reminders (user_id, text, remind_at, done, repeat_type, repeat_every, active) "
        "VALUES (?, ?, ?, 0, ?, ?, 1)",
        (user_id, (text or "")[:300], remind_at, repeat_type or "once", int(repeat_every or 0)),
    )
    rid = c.lastrowid
    conn.commit()
    conn.close()
    return rid

def get_pending_reminders(before_time=None):
    conn = get_db_connection()
    c = conn.cursor()
    if before_time:
        c.execute(
            "SELECT id, user_id, text, remind_at, COALESCE(repeat_type,'once'), "
            "COALESCE(repeat_every,0), COALESCE(active,1) "
            "FROM reminders WHERE done = 0 AND COALESCE(active,1) = 1 AND remind_at <= ?",
            (before_time,),
        )
    else:
        c.execute(
            "SELECT id, user_id, text, remind_at, COALESCE(repeat_type,'once'), "
            "COALESCE(repeat_every,0), COALESCE(active,1) "
            "FROM reminders WHERE done = 0 AND COALESCE(active,1) = 1"
        )
    rows = c.fetchall()
    conn.close()
    return rows

def mark_reminder_done(rid):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE reminders SET done = 1, active = 0 WHERE id = ?", (rid,))
    conn.commit()
    conn.close()

def reschedule_reminder(rid, next_at):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE reminders SET remind_at = ?, done = 0, active = 1 WHERE id = ?",
        (next_at, rid),
    )
    conn.commit()
    conn.close()

def list_user_reminders(user_id, limit=20):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "SELECT id, text, remind_at, COALESCE(repeat_type,'once'), COALESCE(repeat_every,0), "
        "COALESCE(done,0), COALESCE(active,1) FROM reminders "
        "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit),
    )
    rows = c.fetchall()
    conn.close()
    return rows

def cancel_reminder(user_id, rid):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE reminders SET done = 1, active = 0 WHERE id = ? AND user_id = ?",
        (rid, user_id),
    )
    conn.commit()
    n = c.rowcount
    conn.close()
    return n > 0

def set_reminder_active(user_id, rid, active):
    conn = get_db_connection()
    c = conn.cursor()
    if active:
        c.execute("UPDATE reminders SET active=1, done=0 WHERE id=? AND user_id=?", (rid, user_id))
    else:
        c.execute("UPDATE reminders SET active=0 WHERE id=? AND user_id=?", (rid, user_id))
    conn.commit()
    ok = c.rowcount > 0
    conn.close()
    return ok

def update_reminder(user_id, rid, text=None, remind_at=None, repeat_type=None, repeat_every=None):
    conn = get_db_connection()
    c = conn.cursor()
    fields, values = [], []
    if text is not None:
        fields.append("text=?"); values.append((text or "یادآوری")[:300])
    if remind_at is not None:
        fields.append("remind_at=?"); values.append(remind_at)
    if repeat_type is not None:
        fields.append("repeat_type=?"); values.append(repeat_type)
    if repeat_every is not None:
        fields.append("repeat_every=?"); values.append(int(repeat_every or 0))
    if not fields:
        conn.close(); return False
    fields += ["done=0", "active=1"]
    values.extend([rid, user_id])
    c.execute(f"UPDATE reminders SET {', '.join(fields)} WHERE id=? AND user_id=?", values)
    conn.commit(); ok = c.rowcount > 0; conn.close(); return ok

def delete_reminder(user_id, rid):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM reminders WHERE id=? AND user_id=?", (rid, user_id))
    conn.commit(); ok = c.rowcount > 0; conn.close(); return ok
