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
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
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
        for col, default in (
            ("mention_only", "INTEGER DEFAULT 0"),
            ("admin_only", "INTEGER DEFAULT 0"),
            ("fast_path", "INTEGER DEFAULT 1"),
            ("max_answer_chars", "INTEGER DEFAULT 900"),
            ("short_replies", "INTEGER DEFAULT 1"),
            ("ai_enabled", "INTEGER DEFAULT 1"),
        ):
            try:
                c.execute(f"ALTER TABLE group_settings ADD COLUMN {col} {default}")
            except Exception:
                pass
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.warning("ensure_group_settings_table: %s", exc)


def get_group_settings(chat_id: int) -> Dict[str, Any]:
    ensure_group_settings_table()
    try:
        conn = get_db_connection()
        c = conn.cursor()
        row = c.execute(
            "SELECT ai_enabled, short_replies, max_answer_chars, mention_only, admin_only, fast_path "
            "FROM group_settings WHERE chat_id=?",
            (int(chat_id),),
        ).fetchone()
        conn.close()
        if not row:
            return dict(_DEFAULTS)
        return {
            "ai_enabled": int(row[0] if row[0] is not None else 1),
            "short_replies": int(row[1] if row[1] is not None else 1),
            "max_answer_chars": int(row[2] if row[2] is not None else 900),
            "mention_only": int(row[3] if row[3] is not None else 0),
            "admin_only": int(row[4] if row[4] is not None else 0),
            "fast_path": int(row[5] if row[5] is not None else 1),
        }
    except Exception as exc:
        logger.debug("get_group_settings: %s", exc)
        return dict(_DEFAULTS)


def set_group_setting(chat_id: int, key: str, value: int, updated_by: Optional[int] = None) -> bool:
    ensure_group_settings_table()
    if key not in _DEFAULTS:
        return False
    try:
        conn = get_db_connection()
        c = conn.cursor()
        # upsert
        c.execute(
            "INSERT INTO group_settings (chat_id, updated_at, updated_by) VALUES (?, datetime('now'), ?) "
            "ON CONFLICT(chat_id) DO UPDATE SET updated_at=datetime('now'), updated_by=excluded.updated_by",
            (int(chat_id), updated_by),
        )
        c.execute(
            f"UPDATE group_settings SET {key}=?, updated_at=datetime('now'), updated_by=? WHERE chat_id=?",
            (int(value), updated_by, int(chat_id)),
        )
        conn.commit()
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
    return int(get_group_settings(chat_id).get("max_answer_chars", 900) or 900)


def group_mention_only(chat_id: int) -> bool:
    return bool(get_group_settings(chat_id).get("mention_only", 0))


def group_admin_only(chat_id: int) -> bool:
    return bool(get_group_settings(chat_id).get("admin_only", 0))


def group_fast_path_enabled(chat_id: int) -> bool:
    return bool(get_group_settings(chat_id).get("fast_path", 1))
