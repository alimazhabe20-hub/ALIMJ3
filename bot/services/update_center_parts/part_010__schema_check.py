from typing import Any

# Auto-split part 10: _schema_check
def _schema_check() -> dict[str, Any]:
    try:
        if not Path(DB_PATH).exists():
            return {"ok": True, "status": "database_not_created_yet"}
        from bot.database_migrations import schema_status
        conn = sqlite3.connect(DB_PATH)
        try:
            status = schema_status(conn)
        finally:
            conn.close()
        return {"ok": int(status["version"]) <= int(status["supported_version"]), "status": status}
    except Exception:
        return {"ok": False, "status": "schema_check_failed"}
