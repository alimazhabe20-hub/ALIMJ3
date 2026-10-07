# Auto-split part 41: init_v76_tables
def init_v76_tables()->None:
    c=_db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS v76_perf(id INTEGER PRIMARY KEY AUTOINCREMENT,component TEXT,latency_ms REAL,ok INTEGER,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS v76_memory(id TEXT PRIMARY KEY,user_id INTEGER NOT NULL,category TEXT NOT NULL,key TEXT NOT NULL,value TEXT NOT NULL,confidence REAL,source TEXT,updated_at TEXT DEFAULT CURRENT_TIMESTAMP,UNIQUE(user_id,category,key));
    CREATE TABLE IF NOT EXISTS v76_workspaces(id TEXT PRIMARY KEY,user_id INTEGER NOT NULL,name TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS v76_state(user_id INTEGER PRIMARY KEY,goal TEXT,context_json TEXT,pending INTEGER DEFAULT 0,updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS v76_jobs(id TEXT PRIMARY KEY,user_id INTEGER,status TEXT,payload_json TEXT,priority INTEGER DEFAULT 0,attempts INTEGER DEFAULT 0,created_at TEXT DEFAULT CURRENT_TIMESTAMP,updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE INDEX IF NOT EXISTS idx_v76_jobs_status ON v76_jobs(status,priority,created_at);
    CREATE TABLE IF NOT EXISTS v76_security(id INTEGER PRIMARY KEY AUTOINCREMENT,event TEXT,detail TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    """);c.commit();c.close()
