# Auto-split part 18: init_extra_tables
def init_extra_tables():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "CREATE TABLE IF NOT EXISTS notes ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "user_id INTEGER,"
        "content TEXT,"
        "created_at TEXT DEFAULT (datetime('now')))"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS reminders ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "user_id INTEGER,"
        "text TEXT,"
        "remind_at TEXT,"
        "done INTEGER DEFAULT 0,"
        "created_at TEXT DEFAULT (datetime('now')),"
        "repeat_type TEXT DEFAULT 'once',"
        "repeat_every INTEGER DEFAULT 0,"
        "active INTEGER DEFAULT 1)"
    )
    for col, typ in (
        ("repeat_type", "TEXT DEFAULT 'once'"),
        ("repeat_every", "INTEGER DEFAULT 0"),
        ("active", "INTEGER DEFAULT 1"),
    ):
        try:
            c.execute(f"ALTER TABLE reminders ADD COLUMN {col} {typ}")
        except Exception as _exc:
            logger.debug("%s: %s", __name__, _exc)
    c.execute(
        "CREATE TABLE IF NOT EXISTS ai_memory ("
        "user_id INTEGER NOT NULL,"
        "key TEXT NOT NULL,"
        "value TEXT NOT NULL,"
        "updated_at TEXT DEFAULT (datetime('now')),"
        "PRIMARY KEY (user_id, key))"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS ai_history_summary ("
        "user_id INTEGER PRIMARY KEY,"
        "summary TEXT,"
        "updated_at TEXT DEFAULT (datetime('now')))"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS usage_stats ("
        "user_id INTEGER,"
        "feature TEXT,"
        "count INTEGER DEFAULT 1,"
        "last_used TEXT,"
        "PRIMARY KEY (user_id, feature))"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS sent_jokes ("
        "user_id INTEGER,"
        "joke_hash TEXT,"
        "sent_at TEXT DEFAULT (datetime('now')),"
        "PRIMARY KEY (user_id, joke_hash))"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS ai_preferences ("
        "user_id INTEGER PRIMARY KEY,"
        "provider TEXT NOT NULL,"
        "model TEXT DEFAULT '*',"
        "updated_at TEXT DEFAULT (datetime('now')))"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS user_preferences ("
        "user_id INTEGER PRIMARY KEY,"
        "response_style TEXT DEFAULT 'balanced',"
        "currency TEXT DEFAULT 'USD',"
        "updated_at TEXT DEFAULT (datetime('now')))"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS automation_preferences ("
        "user_id INTEGER PRIMARY KEY,"
        "daily_digest INTEGER DEFAULT 0,"
        "last_digest_date TEXT,"
        "updated_at TEXT DEFAULT (datetime('now')))"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS economic_calendar_preferences ("
        "user_id INTEGER PRIMARY KEY,"
        "alerts INTEGER DEFAULT 0,"
        "lead_minutes INTEGER DEFAULT 15,"
        "timezone TEXT DEFAULT '',"
        "currencies TEXT DEFAULT '',"
        "impact TEXT DEFAULT 'high',"
        "updated_at TEXT DEFAULT (datetime('now'))"
        ")"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS economic_calendar_sent ("
        "user_id INTEGER NOT NULL,"
        "event_id TEXT NOT NULL,"
        "sent_at TEXT DEFAULT (datetime('now')),"
        "PRIMARY KEY (user_id, event_id)"
        ")"
    )
    # داده‌های تقویم اقتصادی به‌صورت دائمی نگهداری می‌شوند تا رویدادهای گذشته
    # و مقدار Actual بعد از انتشار از بین نروند.
    c.execute(
        "CREATE TABLE IF NOT EXISTS economic_calendar_events ("
        "event_id TEXT PRIMARY KEY,"
        "utc TEXT NOT NULL,"
        "country TEXT DEFAULT '',"
        "currency_name TEXT DEFAULT '',"
        "impact TEXT DEFAULT '',"
        "title TEXT DEFAULT '',"
        "title_fa TEXT DEFAULT '',"
        "actual TEXT DEFAULT '',"
        "forecast TEXT DEFAULT '',"
        "previous TEXT DEFAULT '',"
        "source TEXT DEFAULT '',"
        "updated_at TEXT DEFAULT (datetime('now'))"
        ")"
    )
    c.execute("CREATE INDEX IF NOT EXISTS idx_economic_calendar_events_utc ON economic_calendar_events(utc)")
    c.execute(
        "CREATE TABLE IF NOT EXISTS agent_learning ("
        "user_id INTEGER NOT NULL,"
        "agent TEXT NOT NULL,"
        "tool TEXT NOT NULL,"
        "success_count INTEGER DEFAULT 0,"
        "failure_count INTEGER DEFAULT 0,"
        "last_success TEXT,"
        "last_failure TEXT,"
        "last_error TEXT,"
        "updated_at TEXT DEFAULT (datetime('now')),"
        "PRIMARY KEY (user_id, agent, tool))"
    )
    try:
        c.execute("ALTER TABLE users ADD COLUMN birth_date TEXT")
    except Exception as _exc:
        logger.debug("%s: %s", __name__, _exc)
    # Indexes for the hottest read paths; CREATE IF NOT EXISTS is safe for upgrades.
    for sql in (
        "CREATE INDEX IF NOT EXISTS idx_users_subscribed ON users(subscribed)",
        "CREATE INDEX IF NOT EXISTS idx_users_last_active ON users(last_active)",
        "CREATE INDEX IF NOT EXISTS idx_reminders_pending ON reminders(done, active, remind_at)",
        "CREATE INDEX IF NOT EXISTS idx_reminders_user ON reminders(user_id, done, active)",
        "CREATE INDEX IF NOT EXISTS idx_notes_user ON notes(user_id, id DESC)",
        "CREATE INDEX IF NOT EXISTS idx_sent_jokes_user_time ON sent_jokes(user_id, sent_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_usage_feature ON usage_stats(feature, count DESC)",
        "CREATE INDEX IF NOT EXISTS idx_agent_learning_user ON agent_learning(user_id, agent, tool)",
        "CREATE INDEX IF NOT EXISTS idx_economic_calendar_sent_user ON economic_calendar_sent(user_id, sent_at DESC)",
    ):
        c.execute(sql)
    conn.commit()
    conn.close()
