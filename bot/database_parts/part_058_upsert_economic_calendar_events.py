# Auto-split part 58: upsert_economic_calendar_events
def upsert_economic_calendar_events(events):
    """ذخیره/به‌روزرسانی رویدادها بدون حذف تاریخچه.

    مقدارهای خالی از منبع، مقدار قبلی ذخیره‌شده را overwrite نمی‌کنند؛ این برای
    Actual مهم است چون منبع ممکن است بین دو refresh آن را موقتاً خالی برگرداند.
    """
    rows = []
    for e in events or []:
        try:
            utc = e.get("utc")
            utc_s = utc.isoformat() if hasattr(utc, "isoformat") else str(utc or "")
            if not e.get("id") or not utc_s:
                continue
            rows.append((
                str(e["id"]), utc_s, str(e.get("country") or ""),
                str(e.get("currency_name") or ""), str(e.get("impact") or ""),
                str(e.get("title") or ""), str(e.get("title_fa") or ""),
                str(e.get("actual") if e.get("actual") is not None else ""),
                str(e.get("forecast") if e.get("forecast") is not None else ""),
                str(e.get("previous") if e.get("previous") is not None else ""),
                str(e.get("source") or ""),
            ))
        except Exception:
            continue
    if not rows:
        return
    conn = get_db_connection()
    try:
        conn.executemany(
            "INSERT INTO economic_calendar_events "
            "(event_id,utc,country,currency_name,impact,title,title_fa,actual,forecast,previous,source,updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,datetime('now')) "
            "ON CONFLICT(event_id) DO UPDATE SET "
            "utc=excluded.utc,country=excluded.country,currency_name=excluded.currency_name,"
            "impact=excluded.impact,title=excluded.title,title_fa=excluded.title_fa,"
            "actual=CASE WHEN excluded.actual <> '' THEN excluded.actual ELSE economic_calendar_events.actual END,"
            "forecast=CASE WHEN excluded.forecast <> '' THEN excluded.forecast ELSE economic_calendar_events.forecast END,"
            "previous=CASE WHEN excluded.previous <> '' THEN excluded.previous ELSE economic_calendar_events.previous END,"
            "source=CASE WHEN excluded.source <> '' THEN excluded.source ELSE economic_calendar_events.source END,"
            "updated_at=datetime('now')",
            rows,
        )
        conn.commit()
    finally:
        conn.close()
