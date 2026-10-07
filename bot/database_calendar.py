"""database: calendar responsibilities."""
from .database_common import *  # noqa: F401,F403
from . import database_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


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

def get_economic_calendar_event(event_id):
    conn = get_db_connection()
    try:
        return conn.execute(
            "SELECT event_id,utc,country,currency_name,impact,title,title_fa,actual,forecast,previous,source FROM economic_calendar_events WHERE event_id=?",
            (event_id,),
        ).fetchone()
    finally:
        conn.close()

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

def get_economic_calendar_alert_users():
    conn = get_db_connection()
    try:
        return conn.execute(
            "SELECT p.user_id, p.lead_minutes, p.timezone, p.currencies, p.impact "
            "FROM economic_calendar_preferences p JOIN users u ON u.user_id=p.user_id "
            "WHERE p.alerts=1 AND u.subscribed=1"
        ).fetchall()
    finally:
        conn.close()

def economic_calendar_alert_was_sent(user_id, event_id):
    conn = get_db_connection()
    try:
        return conn.execute(
            "SELECT 1 FROM economic_calendar_sent WHERE user_id=? AND event_id=?",
            (user_id, event_id),
        ).fetchone() is not None
    finally:
        conn.close()

def mark_economic_calendar_alert_sent(user_id, event_id):
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO economic_calendar_sent(user_id,event_id,sent_at) VALUES(?,?,datetime('now'))",
            (user_id, event_id),
        )
        conn.commit()
    finally:
        conn.close()
