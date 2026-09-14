# Auto-split part 61: init_v77_tables
def init_v77_tables() -> None:
    c=_db();c.executescript("""
    CREATE TABLE IF NOT EXISTS v77_graph_nodes(id TEXT PRIMARY KEY,label TEXT NOT NULL,kind TEXT NOT NULL,properties_json TEXT,updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS v77_graph_edges(source TEXT NOT NULL,relation TEXT NOT NULL,target TEXT NOT NULL,weight REAL DEFAULT 1,PRIMARY KEY(source,relation,target));
    CREATE TABLE IF NOT EXISTS v77_perf(id INTEGER PRIMARY KEY AUTOINCREMENT,component TEXT,latency_ms REAL,ok INTEGER,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS v77_alerts(id TEXT PRIMARY KEY,user_id INTEGER NOT NULL,kind TEXT NOT NULL,config_json TEXT NOT NULL,enabled INTEGER DEFAULT 1,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS v77_conversation(id TEXT PRIMARY KEY,user_id INTEGER NOT NULL,role TEXT NOT NULL,content TEXT NOT NULL,metadata_json TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE INDEX IF NOT EXISTS idx_v77_graph_edges_source ON v77_graph_edges(source);
    CREATE INDEX IF NOT EXISTS idx_v77_alerts_user ON v77_alerts(user_id,enabled);
    CREATE INDEX IF NOT EXISTS idx_v77_conversation_user ON v77_conversation(user_id,created_at);
    """);c.commit();c.close()
