# Auto-split part 25: add_reminder
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
