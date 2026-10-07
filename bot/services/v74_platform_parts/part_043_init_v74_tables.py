# Auto-split part 43: init_v74_tables
def init_v74_tables() -> None:
    try:
        from bot.database import get_db_connection
        conn=get_db_connection()
        conn.execute("CREATE TABLE IF NOT EXISTS v74_events (id INTEGER PRIMARY KEY AUTOINCREMENT, component TEXT, event TEXT, detail TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_v74_events_component_time ON v74_events(component, created_at)")
        conn.execute("CREATE TABLE IF NOT EXISTS v74_provider (provider TEXT PRIMARY KEY, calls INTEGER DEFAULT 0, errors INTEGER DEFAULT 0, total_ms REAL DEFAULT 0, cooldown_until REAL DEFAULT 0, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)")
        conn.execute("CREATE TABLE IF NOT EXISTS v74_backups (path TEXT PRIMARY KEY, sha256 TEXT, users INTEGER DEFAULT 0, integrity_ok INTEGER DEFAULT 0, verified_at TEXT DEFAULT CURRENT_TIMESTAMP)")
        conn.commit(); conn.close()
    except Exception as exc:
        logger.warning("V74 table initialization failed: %s", exc)
