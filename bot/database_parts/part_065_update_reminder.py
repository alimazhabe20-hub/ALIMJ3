# Auto-split part 65: update_reminder
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
