"""تنظیمات اختصاصی هر گروه."""
from __future__ import annotations

from typing import Optional, Dict, Any

from bot.database_core import get_db_connection
from bot.logger import logger

_DEFAULTS = {
    "ai_enabled": 1,
    "short_replies": 1,
    "max_answer_chars": 900,
    "mention_only": 0,
    "admin_only": 0,
    "fast_path": 1,
}


def ensure_group_settings_table() -> None:
    """Create/migrate group settings without masking unrelated schema errors."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS group_settings (
                chat_id INTEGER PRIMARY KEY,
                ai_enabled INTEGER DEFAULT 1,
                short_replies INTEGER DEFAULT 1,
                max_answer_chars INTEGER DEFAULT 900,
                mention_only INTEGER DEFAULT 0,
                admin_only INTEGER DEFAULT 0,
                fast_path INTEGER DEFAULT 1,
                updated_at TEXT DEFAULT (datetime('now')),
                updated_by INTEGER
            )
            """
        )
        existing = {
            str(row[1]) for row in cursor.execute("PRAGMA table_info(group_settings)").fetchall()
        }
        migrations = {
            "ai_enabled": "INTEGER DEFAULT 1",
            "short_replies": "INTEGER DEFAULT 1",
            "max_answer_chars": "INTEGER DEFAULT 900",
            "mention_only": "INTEGER DEFAULT 0",
            "admin_only": "INTEGER DEFAULT 0",
            "fast_path": "INTEGER DEFAULT 1",
            "updated_at": "TEXT DEFAULT (datetime('now'))",
            "updated_by": "INTEGER",
        }
        for column, definition in migrations.items():
            if column not in existing:
                cursor.execute(f"ALTER TABLE group_settings ADD COLUMN {column} {definition}")
        conn.commit()
    except Exception as exc:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        logger.warning("ensure_group_settings_table: %s", exc)
        raise
    finally:
        if conn is not None:
            conn.close()


def get_group_settings(chat_id: int) -> Dict[str, Any]:
    ensure_group_settings_table()
    conn = None
    try:
        conn = get_db_connection()
        row = conn.execute(
            "SELECT ai_enabled, short_replies, max_answer_chars, mention_only, admin_only, fast_path "
            "FROM group_settings WHERE chat_id=?",
            (int(chat_id),),
        ).fetchone()
        if not row:
            return dict(_DEFAULTS)
        return {
            "ai_enabled": int(row[0] if row[0] is not None else 1),
            "short_replies": int(row[1] if row[1] is not None else 1),
            "max_answer_chars": max(200, min(4000, int(row[2] if row[2] is not None else 900))),
            "mention_only": int(row[3] if row[3] is not None else 0),
            "admin_only": int(row[4] if row[4] is not None else 0),
            "fast_path": int(row[5] if row[5] is not None else 1),
        }
    except Exception as exc:
        logger.warning("get_group_settings: %s", exc)
        return dict(_DEFAULTS)
    finally:
        if conn is not None:
            conn.close()



def set_group_setting(chat_id: int, key: str, value: int, updated_by: Optional[int] = None) -> bool:
    if key not in _DEFAULTS:
        return False
    try:
        numeric_value = int(value)
        if key == "max_answer_chars":
            numeric_value = max(200, min(4000, numeric_value))
        else:
            numeric_value = 1 if numeric_value else 0
        conn = get_db_connection()
        try:
            conn.execute(
                "INSERT INTO group_settings (chat_id, updated_at, updated_by) VALUES (?, datetime('now'), ?) "
                "ON CONFLICT(chat_id) DO UPDATE SET updated_at=datetime('now'), updated_by=excluded.updated_by",
                (int(chat_id), updated_by),
            )
            conn.execute(
                f"UPDATE group_settings SET {key}=?, updated_at=datetime('now'), updated_by=? WHERE chat_id=?",
                (numeric_value, updated_by, int(chat_id)),
            )
            conn.commit()
        finally:
            conn.close()
        return True
    except Exception as exc:
        logger.warning("set_group_setting: %s", exc)
        return False


def is_group_ai_enabled(chat_id: int) -> bool:
    return bool(get_group_settings(chat_id).get("ai_enabled", 1))


def group_wants_short(chat_id: int) -> bool:
    return bool(get_group_settings(chat_id).get("short_replies", 1))


def group_max_chars(chat_id: int) -> int:
    return max(200, min(4000, int(get_group_settings(chat_id).get("max_answer_chars", 900) or 900)))


def group_mention_only(chat_id: int) -> bool:
    return bool(get_group_settings(chat_id).get("mention_only", 0))


def group_admin_only(chat_id: int) -> bool:
    return bool(get_group_settings(chat_id).get("admin_only", 0))


def group_fast_path_enabled(chat_id: int) -> bool:
    return bool(get_group_settings(chat_id).get("fast_path", 1))
