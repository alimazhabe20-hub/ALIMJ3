# Auto-split part 16: init_v73_tables
def init_v73_tables() -> None:
    """Create persistent operational tables without touching existing user data."""
    try:
        from bot.database import get_db_connection
        conn = get_db_connection()
        conn.execute("""CREATE TABLE IF NOT EXISTS v73_health (
            component TEXT PRIMARY KEY, failures INTEGER DEFAULT 0, cooldown_until REAL DEFAULT 0,
            last_error TEXT DEFAULT '', updated_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS v73_perf (
            name TEXT PRIMARY KEY, calls INTEGER DEFAULT 0, errors INTEGER DEFAULT 0,
            total_ms REAL DEFAULT 0, max_ms REAL DEFAULT 0, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.warning("V73 table initialization failed: %s", exc)
