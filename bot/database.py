"""Public compatibility facade for database.

Semantically split into focused modules; historical imports remain stable.
"""
import importlib as _importlib

from bot.logger import logger
from bot.database_migrations import SCHEMA_VERSION, schema_status

_database_common = _importlib.import_module(".database_common", __package__)
_database_core = _importlib.import_module(".database_core", __package__)
_database_users = _importlib.import_module(".database_users", __package__)
_database_notifications = _importlib.import_module(".database_notifications", __package__)
_database_reminders = _importlib.import_module(".database_reminders", __package__)
_database_ai = _importlib.import_module(".database_ai", __package__)
_database_calendar = _importlib.import_module(".database_calendar", __package__)
_database_stats = _importlib.import_module(".database_stats", __package__)

# Wire all split modules into one compatible namespace so legacy cross-function
# references keep resolving without duplicating implementation.
_split_modules = [_database_common,_database_core,_database_users,_database_notifications,_database_reminders,_database_ai,_database_calendar,_database_stats]
for _m in _split_modules:
    for _o in _split_modules:
        if _m is not _o:
            for _k, _v in _o.__dict__.items():
                if not _k.startswith("__"):
                    _m.__dict__.setdefault(_k, _v)

# Execute late registrations/aliases only after every implementation module is loaded.
_database_registration = _importlib.import_module(".database_registration", __package__)
_split_modules.append(_database_registration)
for _k, _v in _database_registration.__dict__.items():
    if not _k.startswith("__"):
        globals()[_k] = _v



# ---------------------------------------------------------------------------
# Core schema bootstrap
# ---------------------------------------------------------------------------
# The database layer was split into feature modules, but the original schema
# bootstrap was accidentally dropped from the public facade. Keep initialization
# here so every historical ``from bot.database import ...`` caller remains
# compatible and existing SQLite files are upgraded in-place without data loss.
_CORE_SCHEMA = (
    """CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        first_name TEXT,
        city TEXT DEFAULT 'قم',
        country TEXT DEFAULT 'Iran',
        language TEXT DEFAULT 'fa',
        subscribed INTEGER NOT NULL DEFAULT 1,
        register_date TEXT DEFAULT CURRENT_TIMESTAMP,
        last_active TEXT DEFAULT CURRENT_TIMESTAMP,
        notification_enabled INTEGER NOT NULL DEFAULT 0,
        notify_fajr INTEGER NOT NULL DEFAULT 0,
        notify_dhuhr INTEGER NOT NULL DEFAULT 0,
        notify_asr INTEGER NOT NULL DEFAULT 0,
        notify_maghrib INTEGER NOT NULL DEFAULT 0,
        notify_isha INTEGER NOT NULL DEFAULT 0,
        birth_date TEXT,
        last_main_msg_id INTEGER
    )""",
    """CREATE TABLE IF NOT EXISTS stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        total_users INTEGER NOT NULL DEFAULT 0,
        active_users INTEGER NOT NULL DEFAULT 0
    )""",
    """CREATE TABLE IF NOT EXISTS user_preferences (
        user_id INTEGER PRIMARY KEY,
        response_style TEXT DEFAULT 'balanced',
        currency TEXT DEFAULT 'USD',
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS usage_stats (
        user_id INTEGER NOT NULL,
        feature TEXT NOT NULL,
        count INTEGER NOT NULL DEFAULT 0,
        last_used TEXT DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY(user_id, feature),
        FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS ai_memory (
        user_id INTEGER NOT NULL,
        key TEXT NOT NULL,
        value TEXT NOT NULL,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY(user_id, key),
        FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS ai_history_summary (
        user_id INTEGER PRIMARY KEY,
        summary TEXT DEFAULT '',
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS ai_preferences (
        user_id INTEGER PRIMARY KEY,
        provider TEXT NOT NULL,
        model TEXT DEFAULT '*',
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS agent_learning (
        user_id INTEGER NOT NULL,
        agent TEXT NOT NULL,
        tool TEXT NOT NULL,
        success_count INTEGER NOT NULL DEFAULT 0,
        failure_count INTEGER NOT NULL DEFAULT 0,
        last_error TEXT DEFAULT '',
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY(user_id, agent, tool),
        FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        text TEXT NOT NULL,
        remind_at TEXT NOT NULL,
        done INTEGER NOT NULL DEFAULT 0,
        repeat_type TEXT DEFAULT 'once',
        repeat_every INTEGER DEFAULT 0,
        active INTEGER NOT NULL DEFAULT 1,
        FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS sent_jokes (
        user_id INTEGER NOT NULL,
        joke_hash TEXT NOT NULL,
        sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY(user_id, joke_hash),
        FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS automation_preferences (
        user_id INTEGER PRIMARY KEY,
        daily_digest INTEGER NOT NULL DEFAULT 0,
        last_digest_date TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS economic_calendar_preferences (
        user_id INTEGER PRIMARY KEY,
        alerts INTEGER NOT NULL DEFAULT 0,
        lead_minutes INTEGER NOT NULL DEFAULT 15,
        timezone TEXT DEFAULT '',
        currencies TEXT DEFAULT '',
        impact TEXT DEFAULT 'all',
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS economic_calendar_events (
        event_id TEXT PRIMARY KEY,
        utc TEXT NOT NULL,
        country TEXT DEFAULT '',
        currency_name TEXT DEFAULT '',
        impact TEXT DEFAULT '',
        title TEXT DEFAULT '',
        title_fa TEXT DEFAULT '',
        actual TEXT DEFAULT '',
        forecast TEXT DEFAULT '',
        previous TEXT DEFAULT '',
        source TEXT DEFAULT '',
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS economic_calendar_sent (
        user_id INTEGER NOT NULL,
        event_id TEXT NOT NULL,
        sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY(user_id, event_id),
        FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
    )""",
)

_CORE_COLUMNS = {
    "users": {
        "birth_date": "TEXT",
        "last_main_msg_id": "INTEGER",
    },
    "reminders": {
        "repeat_type": "TEXT DEFAULT 'once'",
        "repeat_every": "INTEGER DEFAULT 0",
        "active": "INTEGER NOT NULL DEFAULT 1",
    },
    "economic_calendar_events": {
        "updated_at": "TEXT DEFAULT CURRENT_TIMESTAMP",
    },
}


def _table_columns(conn, table):
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _ensure_core_columns(conn):
    for table, columns in _CORE_COLUMNS.items():
        existing = _table_columns(conn, table)
        for column, definition in columns.items():
            if column not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db():
    """Create/upgrade the core SQLite schema and register schema version.

    This is intentionally idempotent and data-preserving. It also performs the
    platform table initializers so a fresh Render instance is fully bootable,
    while failures in optional platform tables are surfaced instead of being
    silently ignored.
    """
    _database_core._ensure_parent(_database_core._current_db_path())
    conn = _database_core.get_db_connection()
    try:
        for sql in _CORE_SCHEMA:
            conn.execute(sql)
        _ensure_core_columns(conn)
        conn.commit()
        _database_migrations = _importlib.import_module(".database_migrations", __package__)
        _database_migrations.ensure_schema_version(conn, _database_core._current_db_path())
        conn.commit()
    finally:
        conn.close()

    # Platform tables are independent and idempotent. Initialize them after
    # the core users/schema tables exist, preserving the existing architecture.
    platform_initializers = (
        ("bot.services.v61_v65_platform", "init_platform_tables"),
        ("bot.services.v70_platform", "init_v70_tables"),
        ("bot.services.v71_platform", "init_v71_tables"),
        ("bot.services.v72_platform", "init_v72_tables"),
        ("bot.services.v73_platform", "init_v73_tables"),
        ("bot.services.v74_platform_runtime", "init_v74_tables"),
        ("bot.services.v75_platform_security", "init_v75_tables"),
        ("bot.services.v76_platform", "init_v76_tables"),
        ("bot.services.v77_platform_runtime", "init_v77_tables"),
    )
    for module_name, func_name in platform_initializers:
        try:
            module = _importlib.import_module(module_name)
            initializer = getattr(module, func_name, None)
            if callable(initializer):
                initializer()
        except Exception as exc:
            # These tables are part of the deployed feature set, so do not
            # pretend startup succeeded when one of them cannot initialize.
            logger.error("Database platform initialization failed: %s.%s: %s", module_name, func_name, exc, exc_info=True)
            raise

    logger.info("Database initialized: %s (schema V%s)", DB_PATH, SCHEMA_VERSION)


def get_schema_status():
    """Return safe database schema metadata for diagnostics/tests."""
    conn = _database_core.get_db_connection()
    try:
        return schema_status(conn)
    finally:
        conn.close()

# Export every historical symbol, including private helpers used by sibling modules.
for _m in _split_modules:
    for _k, _v in _m.__dict__.items():
        if not _k.startswith("__") and _k not in {"_m","_o","_k","_v"}:
            globals()[_k] = _v
