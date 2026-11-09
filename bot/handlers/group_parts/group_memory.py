"""Persistent, group-scoped conversation memory.

Stores speaker-attributed turns and rolling summaries in the bot SQLite DB.
The public add_turn/get_context/clear_chat API remains backward compatible.
"""
from __future__ import annotations

import re
import time
from typing import Optional

from bot.database_core import get_db_connection
from bot.logger import logger

_MAX_TURNS = 80
_CONTEXT_TURNS = 12
_MAX_TURN_CHARS = 2400


def _ensure_tables() -> None:
    conn = get_db_connection()
    try:
        conn.execute("""CREATE TABLE IF NOT EXISTS group_ai_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            message_id INTEGER,
            reply_to_message_id INTEGER,
            user_id INTEGER,
            speaker TEXT NOT NULL DEFAULT 'کاربر',
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_group_ai_memory_chat_id ON group_ai_memory(chat_id, id)")
        conn.execute("""CREATE TABLE IF NOT EXISTS group_ai_summaries (
            chat_id INTEGER PRIMARY KEY,
            summary TEXT NOT NULL DEFAULT '',
            updated_at INTEGER NOT NULL
        )""")
        conn.commit()
    finally:
        conn.close()


def _clean(text: str) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    return text[:_MAX_TURN_CHARS]


def add_turn(
    chat_id: int,
    role: str,
    text: str,
    *,
    user_id: Optional[int] = None,
    speaker: str = "کاربر",
    message_id: Optional[int] = None,
    reply_to_message_id: Optional[int] = None,
) -> None:
    content = _clean(text)
    if not content:
        return
    try:
        _ensure_tables()
        conn = get_db_connection()
        try:
            conn.execute(
                "INSERT INTO group_ai_memory(chat_id,message_id,reply_to_message_id,user_id,speaker,role,content,created_at) VALUES(?,?,?,?,?,?,?,?)",
                (int(chat_id), message_id, reply_to_message_id, user_id, _clean(speaker)[:80] or "کاربر", str(role), content, int(time.time())),
            )
            # Keep a bounded history per group. Summaries preserve older context.
            conn.execute(
                "DELETE FROM group_ai_memory WHERE chat_id=? AND id NOT IN (SELECT id FROM group_ai_memory WHERE chat_id=? ORDER BY id DESC LIMIT ?)",
                (int(chat_id), int(chat_id), _MAX_TURNS),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception as exc:
        logger.warning("group memory add_turn failed: %s", exc)


def get_context(chat_id: int, user_id: Optional[int] = None, reply_to_message_id: Optional[int] = None) -> str:
    try:
        _ensure_tables()
        conn = get_db_connection()
        try:
            row = conn.execute("SELECT summary FROM group_ai_summaries WHERE chat_id=?", (int(chat_id),)).fetchone()
            summary = (row[0] or "").strip() if row else ""
            rows = conn.execute(
                "SELECT id,message_id,reply_to_message_id,user_id,speaker,role,content FROM group_ai_memory WHERE chat_id=? ORDER BY id DESC LIMIT ?",
                (int(chat_id), _CONTEXT_TURNS),
            ).fetchall()
        finally:
            conn.close()
        rows = list(reversed(rows))
        lines = []
        if summary:
            lines.append("خلاصهٔ قبلی گفتگوهای این گروه:\n" + summary[:3000])
        if reply_to_message_id:
            target = next((r for r in rows if r[1] == reply_to_message_id), None)
            if target:
                lines.append(f"پیامی که کاربر به آن Reply کرده، از {target[4]}: {target[6]}")
        for _id, _mid, _reply, uid, speaker, role, content in rows:
            if user_id is not None and uid == user_id and role == "user":
                # Keep the current participant visible, but do not discard other speakers.
                pass
            who = speaker if role == "user" else "دستیار روز زیبا"
            lines.append(f"{who}: {content}")
        return "\n".join(lines)[-8500:]
    except Exception as exc:
        logger.warning("group memory get_context failed: %s", exc)
        return ""


def clear_chat(chat_id: int) -> None:
    try:
        _ensure_tables()
        conn = get_db_connection()
        try:
            conn.execute("DELETE FROM group_ai_memory WHERE chat_id=?", (int(chat_id),))
            conn.execute("DELETE FROM group_ai_summaries WHERE chat_id=?", (int(chat_id),))
            conn.commit()
        finally:
            conn.close()
    except Exception as exc:
        logger.warning("group memory clear failed: %s", exc)


def get_summary(chat_id: int) -> str:
    try:
        _ensure_tables()
        conn = get_db_connection()
        try:
            row = conn.execute("SELECT summary FROM group_ai_summaries WHERE chat_id=?", (int(chat_id),)).fetchone()
            return (row[0] or "") if row else ""
        finally:
            conn.close()
    except Exception:
        return ""


def set_summary(chat_id: int, summary: str) -> None:
    summary = _clean(summary)[:5000]
    if not summary:
        return
    _ensure_tables()
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO group_ai_summaries(chat_id,summary,updated_at) VALUES(?,?,?) ON CONFLICT(chat_id) DO UPDATE SET summary=excluded.summary,updated_at=excluded.updated_at",
            (int(chat_id), summary, int(time.time())),
        )
        conn.commit()
    finally:
        conn.close()


async def summarize_group(chat_id: int, user_id: int = 0) -> str:
    """Create/update a compact rolling summary from the group's recent history."""
    context = get_context(chat_id)
    if not context:
        return "هنوز گفتگوی کافی برای خلاصه‌سازی وجود ندارد."
    from bot.services.ai_service import ask_ai
    prompt = (
        "گفتگوی زیر متعلق به یک گروه تلگرام است. آن را به فارسی در ۸ تا ۱۲ نکته خلاصه کن. "
        "نام گویندگان، تصمیم‌ها، سؤال‌های باز، توافق‌ها و موضوعات مهم را حفظ کن. "
        "چیزی را حدس نزن و مکالمه‌ها را به افراد اشتباه نسبت نده.\n\n" + context[-7500:]
    )
    result = await ask_ai(int(user_id or 0), prompt)
    if isinstance(result, tuple):
        result = result[0]
    summary = str(result or "").strip()
    if summary:
        old = get_summary(chat_id)
        merged = (old + "\n" + summary).strip() if old else summary
        # Compress the persisted summary itself to avoid unbounded growth.
        set_summary(chat_id, merged[-4500:])
        return summary
    return "خلاصه‌سازی انجام نشد؛ دوباره تلاش کن."
