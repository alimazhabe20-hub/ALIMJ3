# Auto-split part 7: due_ai_jobs
def due_ai_jobs(limit:int=50)->list[tuple]:
    conn=get_db_connection(); rows=conn.execute("SELECT id,user_id,prompt,run_at,repeat_minutes FROM v71_scheduled_ai WHERE enabled=1 AND run_at<=datetime('now') ORDER BY id LIMIT ?",(max(1,min(200,limit)),)).fetchall(); conn.close(); return rows
