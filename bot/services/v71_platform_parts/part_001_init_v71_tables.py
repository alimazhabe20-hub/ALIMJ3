# Auto-split part 1: init_v71_tables
def init_v71_tables() -> None:
    conn = get_db_connection(); c = conn.cursor()
    for sql in (
        "CREATE TABLE IF NOT EXISTS v71_workspaces (user_id INTEGER NOT NULL, name TEXT NOT NULL, data TEXT NOT NULL, updated_at TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(user_id,name))",
        "CREATE TABLE IF NOT EXISTS v71_branches (user_id INTEGER NOT NULL, name TEXT NOT NULL, context TEXT NOT NULL, updated_at TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(user_id,name))",
        "CREATE TABLE IF NOT EXISTS v71_scheduled_ai (id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,prompt TEXT NOT NULL,run_at TEXT NOT NULL,repeat_minutes INTEGER DEFAULT 0,enabled INTEGER DEFAULT 1,last_run TEXT)",
        "CREATE TABLE IF NOT EXISTS v71_notifications (id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,kind TEXT NOT NULL,payload TEXT NOT NULL,dedupe_key TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP,sent_at TEXT)",
        "CREATE TABLE IF NOT EXISTS v71_health (id INTEGER PRIMARY KEY AUTOINCREMENT,component TEXT NOT NULL,ok INTEGER NOT NULL,latency_ms REAL DEFAULT 0,error_code TEXT DEFAULT '',created_at TEXT DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS v71_user_settings (user_id INTEGER PRIMARY KEY,language TEXT DEFAULT 'fa',response_style TEXT DEFAULT 'balanced',ai_mode TEXT DEFAULT 'balanced',notifications INTEGER DEFAULT 1)",
        "CREATE INDEX IF NOT EXISTS idx_v71_jobs_due ON v71_scheduled_ai(enabled,run_at)",
        "CREATE INDEX IF NOT EXISTS idx_v71_notifications_user ON v71_notifications(user_id,created_at)",
    ):
        c.execute(sql)
    conn.commit(); conn.close()
