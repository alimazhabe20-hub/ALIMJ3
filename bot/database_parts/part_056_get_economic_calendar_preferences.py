# Auto-split part 56: get_economic_calendar_preferences
def get_economic_calendar_preferences(user_id):
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT alerts, lead_minutes, timezone, currencies, impact FROM economic_calendar_preferences WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if not row:
            return {"alerts": False, "lead_minutes": 15, "timezone": "", "currencies": [], "impact": "all"}
        return {
            "alerts": bool(row[0]),
            "lead_minutes": max(1, min(120, int(row[1] or 15))),
            "timezone": row[2] or "",
            "currencies": [x for x in (row[3] or "").split(",") if x],
            "impact": row[4] or "all",
        }
    finally:
        conn.close()
