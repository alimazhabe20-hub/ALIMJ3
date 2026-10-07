# Auto-split part 5: init_v75_tables
def init_v75_tables() -> None:
    conn = _db()
    try:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS v75_workspaces (
            id TEXT PRIMARY KEY, user_id INTEGER NOT NULL, name TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_v75_ws_user ON v75_workspaces(user_id);
        CREATE TABLE IF NOT EXISTS v75_workflow_runs (
            id TEXT PRIMARY KEY, user_id INTEGER NOT NULL, name TEXT NOT NULL,
            status TEXT NOT NULL, input_json TEXT, result_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP, finished_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_v75_runs_user ON v75_workflow_runs(user_id, created_at);
        CREATE TABLE IF NOT EXISTS v75_alerts (
            id TEXT PRIMARY KEY, user_id INTEGER NOT NULL, kind TEXT NOT NULL,
            config_json TEXT NOT NULL, enabled INTEGER DEFAULT 1,
            last_value TEXT, last_fired_at TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_v75_alerts_user ON v75_alerts(user_id, enabled);
        CREATE TABLE IF NOT EXISTS v75_memory (
            id TEXT PRIMARY KEY, user_id INTEGER NOT NULL, category TEXT NOT NULL,
            key TEXT NOT NULL, value TEXT NOT NULL, confidence REAL DEFAULT 1.0,
            source TEXT DEFAULT 'user', updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, category, key)
        );
        CREATE INDEX IF NOT EXISTS idx_v75_mem_user ON v75_memory(user_id, category);
        CREATE TABLE IF NOT EXISTS v75_news (
            id TEXT PRIMARY KEY, source TEXT NOT NULL, title TEXT NOT NULL,
            url TEXT, published_at TEXT, impact REAL DEFAULT 0,
            sentiment REAL DEFAULT 0, content_hash TEXT UNIQUE,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS v75_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT, component TEXT NOT NULL,
            operation TEXT NOT NULL, latency_ms REAL DEFAULT 0, ok INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_v75_metrics_time ON v75_metrics(created_at);
        """)
        conn.commit()
    finally:
        conn.close()
