# Auto-split part 6: schedule_ai
def schedule_ai(user_id:int,prompt:str,run_at:str,repeat_minutes:int=0)->int:
    conn=get_db_connection(); cur=conn.execute("INSERT INTO v71_scheduled_ai(user_id,prompt,run_at,repeat_minutes) VALUES(?,?,?,?)",(user_id,prompt[:4000],run_at,max(0,int(repeat_minutes)))); conn.commit(); jid=int(cur.lastrowid); conn.close(); return jid
