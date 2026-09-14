# Auto-split part 57: set_economic_calendar_preferences
def set_economic_calendar_preferences(user_id, *, alerts=None, lead_minutes=None, timezone=None, currencies=None, impact=None):
    current = get_economic_calendar_preferences(user_id)
    if alerts is not None:
        current["alerts"] = bool(alerts)
    if lead_minutes is not None:
        current["lead_minutes"] = max(1, min(120, int(lead_minutes)))
    if timezone is not None:
        current["timezone"] = str(timezone).strip()[:64]
    if currencies is not None:
        current["currencies"] = [str(x).upper().strip() for x in currencies if str(x).strip()]
    if impact is not None:
        current["impact"] = str(impact).strip().lower()[:16] or "all"
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO economic_calendar_preferences(user_id,alerts,lead_minutes,timezone,currencies,impact,updated_at) "
            "VALUES(?,?,?,?,?,?,datetime('now')) "
            "ON CONFLICT(user_id) DO UPDATE SET alerts=excluded.alerts, lead_minutes=excluded.lead_minutes, "
            "timezone=excluded.timezone, currencies=excluded.currencies, impact=excluded.impact, updated_at=datetime('now')",
            (user_id, 1 if current["alerts"] else 0, current["lead_minutes"], current["timezone"],
             ",".join(current["currencies"]), current["impact"]),
        )
        conn.commit()
    finally:
        conn.close()
    return current
