# Auto-split part 1: init_v72_tables
def init_v72_tables() -> None:
    conn = get_db_connection(); cur = conn.cursor()
    statements = (
        "CREATE TABLE IF NOT EXISTS v72_download_jobs (id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,url TEXT NOT NULL,mode TEXT NOT NULL,status TEXT NOT NULL,progress REAL DEFAULT 0,error_code TEXT DEFAULT '',created_at TEXT DEFAULT CURRENT_TIMESTAMP,updated_at TEXT DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS v72_web_sources (id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,url TEXT NOT NULL,domain TEXT NOT NULL,title TEXT DEFAULT '',score REAL DEFAULT 0,created_at TEXT DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS v72_documents (id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,name TEXT NOT NULL,sha256 TEXT NOT NULL,size INTEGER NOT NULL,kind TEXT NOT NULL,content TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP,UNIQUE(user_id,sha256))",
        "CREATE TABLE IF NOT EXISTS v72_market_cache (symbol TEXT NOT NULL,timeframe TEXT NOT NULL,payload TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP,PRIMARY KEY(symbol,timeframe))",
        "CREATE TABLE IF NOT EXISTS v72_qa_runs (id INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT NOT NULL,ok INTEGER NOT NULL,details TEXT DEFAULT '',created_at TEXT DEFAULT CURRENT_TIMESTAMP)",
        "CREATE INDEX IF NOT EXISTS idx_v72_download_user ON v72_download_jobs(user_id,created_at)",
        "CREATE INDEX IF NOT EXISTS idx_v72_sources_user ON v72_web_sources(user_id,created_at)",
        "CREATE INDEX IF NOT EXISTS idx_v72_docs_user ON v72_documents(user_id,created_at)",
    )
    for sql in statements:
        cur.execute(sql)
    conn.commit(); conn.close()
