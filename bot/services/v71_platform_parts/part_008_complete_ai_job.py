# Auto-split part 8: complete_ai_job
def complete_ai_job(job_id:int,repeat_minutes:int)->None:
    if repeat_minutes>0:
        _execute_write("UPDATE v71_scheduled_ai SET run_at=datetime('now','+' || ? || ' minutes'),last_run=datetime('now') WHERE id=?",(repeat_minutes,job_id))
    else:
        _execute_write("UPDATE v71_scheduled_ai SET enabled=0,last_run=datetime('now') WHERE id=?",(job_id,))
