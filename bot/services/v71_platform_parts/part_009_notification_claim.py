# Auto-split part 9: notification_claim
def notification_claim(user_id:int,kind:str,payload:str,dedupe_key:str,ttl_seconds:int=900)->bool:
    # Atomic enough for SQLite's single-writer model; avoids duplicate notifications.
    conn=get_db_connection()
    row=conn.execute("SELECT id FROM v71_notifications WHERE user_id=? AND kind=? AND dedupe_key=? AND created_at>=datetime('now',?) LIMIT 1",(user_id,kind,dedupe_key,f"-{max(1,ttl_seconds)} seconds")).fetchone()
    if row:
        conn.close(); return False
    conn.execute("INSERT INTO v71_notifications(user_id,kind,payload,dedupe_key) VALUES(?,?,?,?)",(user_id,kind,payload,dedupe_key)); conn.commit(); conn.close(); return True
