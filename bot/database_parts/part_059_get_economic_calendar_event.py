# Auto-split part 59: get_economic_calendar_event
def get_economic_calendar_event(event_id):
    conn = get_db_connection()
    try:
        return conn.execute(
            "SELECT event_id,utc,country,currency_name,impact,title,title_fa,actual,forecast,previous,source FROM economic_calendar_events WHERE event_id=?",
            (event_id,),
        ).fetchone()
    finally:
        conn.close()
