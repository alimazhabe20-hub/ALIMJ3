# Auto-split part 60: get_economic_calendar_events
def get_economic_calendar_events(start_utc=None, end_utc=None):
    """بازیابی تاریخچه تقویم؛ بدون حذف رویدادهای گذشته."""
    conn = get_db_connection()
    try:
        sql = "SELECT event_id,utc,country,currency_name,impact,title,title_fa,actual,forecast,previous,source FROM economic_calendar_events"
        args = []
        clauses = []
        if start_utc is not None:
            clauses.append("utc >= ?")
            args.append(start_utc.isoformat() if hasattr(start_utc, "isoformat") else str(start_utc))
        if end_utc is not None:
            clauses.append("utc < ?")
            args.append(end_utc.isoformat() if hasattr(end_utc, "isoformat") else str(end_utc))
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY utc ASC"
        rows = conn.execute(sql, args).fetchall()
        return rows
    finally:
        conn.close()
