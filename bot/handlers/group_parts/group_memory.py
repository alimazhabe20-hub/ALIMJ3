"""حافظه هوشمند گروه — پایدار، کوتاه، مرتبط با UX تمیز."""
from __future__ import annotations

import re
import time
from typing import Optional

from bot.database_core import get_db_connection
from bot.logger import logger

_MAX_TURNS = 60
_CONTEXT_TURNS = 8
_MAX_TURN_CHARS = 500          # ذخیره کوتاه‌تر = پرامپت تمیزتر
_MAX_BOT_CHARS = 280
_AUTO_SUMMARY_EVERY = 20      # هر ۲۰ نوبت یک خلاصه سبک


def _ensure_tables() -> None:
    conn = get_db_connection()
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS group_ai_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            message_id INTEGER,
            reply_to_message_id INTEGER,
            user_id INTEGER,
            speaker TEXT NOT NULL DEFAULT 'کاربر',
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )"""
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_group_ai_memory_chat_id ON group_ai_memory(chat_id, id)"
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS group_ai_summaries (
            chat_id INTEGER PRIMARY KEY,
            summary TEXT NOT NULL DEFAULT '',
            updated_at INTEGER NOT NULL
        )"""
        )
        conn.commit()
    finally:
        conn.close()


def _clean(text: str, limit: int = _MAX_TURN_CHARS) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    # حذف هدر/فوتر UI از حافظه
    text = re.sub(r"🤖\s*روز زیبا[^\n]*", "", text)
    text = re.sub(r"─{3,}|━{3,}", " ", text)
    text = re.sub(r"💬\s*ریپلای[^\n]*", "", text)
    text = re.sub(r"💡\s*ریپلای[^\n]*", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        text = text[: limit - 1] + "…"
    return text


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
    limit = _MAX_BOT_CHARS if role in {"bot", "assistant"} else _MAX_TURN_CHARS
    content = _clean(text, limit)
    if not content:
        return
    # پیام‌های صرفاً سیستمی/خطا را ذخیره نکن
    if role in {"bot", "assistant"} and any(
        x in content for x in ("در حال نوشتن", "دسترسی ندارم", "الان نتونستم", "⚠️")
    ):
        if len(content) < 40:
            return
    try:
        _ensure_tables()
        conn = get_db_connection()
        try:
            conn.execute(
                "INSERT INTO group_ai_memory(chat_id,message_id,reply_to_message_id,user_id,speaker,role,content,created_at) VALUES(?,?,?,?,?,?,?,?)",
                (
                    int(chat_id),
                    message_id,
                    reply_to_message_id,
                    user_id,
                    _clean(speaker, 40) or "کاربر",
                    "bot" if role in {"bot", "assistant"} else "user",
                    content,
                    int(time.time()),
                ),
            )
            conn.execute(
                "DELETE FROM group_ai_memory WHERE chat_id=? AND id NOT IN "
                "(SELECT id FROM group_ai_memory WHERE chat_id=? ORDER BY id DESC LIMIT ?)",
                (int(chat_id), int(chat_id), _MAX_TURNS),
            )
            conn.commit()
            # شمارش برای auto-summary سبک
            row = conn.execute(
                "SELECT COUNT(*) FROM group_ai_memory WHERE chat_id=?",
                (int(chat_id),),
            ).fetchone()
            count = int(row[0] or 0) if row else 0
        finally:
            conn.close()
        if count and count % _AUTO_SUMMARY_EVERY == 0:
            try:
                _maybe_local_summary(int(chat_id))
            except Exception as exc:
                logger.debug("auto summary skip: %s", exc)
    except Exception as exc:
        logger.warning("group memory add_turn failed: %s", exc)


def _maybe_local_summary(chat_id: int) -> None:
    """خلاصه محلی بدون LLM — فقط از آخرین نوبت‌ها."""
    ctx = get_context(chat_id, max_turns=12, for_prompt=False)
    if not ctx or len(ctx) < 80:
        return
    lines = [ln.strip() for ln in ctx.splitlines() if ln.strip()][-10:]
    bullet = " · ".join(lines)[:900]
    if not bullet:
        return
    old = get_summary(chat_id)
    merged = (old + " | " + bullet).strip(" |") if old else bullet
    set_summary(chat_id, merged[-2000:])


def get_context(
    chat_id: int,
    user_id: Optional[int] = None,
    reply_to_message_id: Optional[int] = None,
    *,
    max_turns: int = _CONTEXT_TURNS,
    for_prompt: bool = True,
) -> str:
    """زمینه کوتاه و مرتب برای پرامپت یا نمایش."""
    try:
        _ensure_tables()
        conn = get_db_connection()
        try:
            row = conn.execute(
                "SELECT summary FROM group_ai_summaries WHERE chat_id=?",
                (int(chat_id),),
            ).fetchone()
            summary = (row[0] or "").strip() if row else ""
            rows = conn.execute(
                "SELECT id,message_id,reply_to_message_id,user_id,speaker,role,content "
                "FROM group_ai_memory WHERE chat_id=? ORDER BY id DESC LIMIT ?",
                (int(chat_id), max(4, min(int(max_turns), 16))),
            ).fetchall()
        finally:
            conn.close()

        rows = list(reversed(rows))
        parts: list[str] = []

        if for_prompt and summary:
            parts.append("خلاصه کوتاه گروه: " + summary[:500])

        # اگر Reply به پیام خاصی شده، همان را برجسته کن
        if reply_to_message_id:
            target = next((r for r in rows if r[1] == reply_to_message_id), None)
            if target:
                who = target[4] if target[5] == "user" else "دستیار"
                parts.append(f"ریپلای به گفتهٔ {who}: {target[6][:220]}")

        # اولویت: پیام‌های همان کاربر + ۲ نوبت عمومی آخر
        same_user = []
        others = []
        for r in rows:
            if user_id is not None and r[3] == user_id:
                same_user.append(r)
            else:
                others.append(r)
        ordered = (same_user[-4:] + others[-4:]) if user_id is not None else rows
        # unique by id preserve order
        seen = set()
        final_rows = []
        for r in ordered:
            if r[0] in seen:
                continue
            seen.add(r[0])
            final_rows.append(r)
        final_rows = final_rows[-max_turns:]

        for _id, _mid, _reply, uid, speaker, role, content in final_rows:
            who = speaker if role == "user" else "دستیار"
            parts.append(f"{who}: {content}")

        text = "\n".join(parts)
        if for_prompt:
            return text[-1800:]  # پرامپت سبک برای سرعت
        return text[-3500:]
    except Exception as exc:
        logger.warning("group memory get_context failed: %s", exc)
        return ""


def memory_stats(chat_id: int) -> dict:
    try:
        _ensure_tables()
        conn = get_db_connection()
        try:
            n = conn.execute(
                "SELECT COUNT(*) FROM group_ai_memory WHERE chat_id=?",
                (int(chat_id),),
            ).fetchone()
            s = conn.execute(
                "SELECT LENGTH(summary), updated_at FROM group_ai_summaries WHERE chat_id=?",
                (int(chat_id),),
            ).fetchone()
        finally:
            conn.close()
        return {
            "turns": int(n[0] or 0) if n else 0,
            "summary_len": int(s[0] or 0) if s else 0,
            "summary_at": int(s[1] or 0) if s else 0,
        }
    except Exception:
        return {"turns": 0, "summary_len": 0, "summary_at": 0}


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
            row = conn.execute(
                "SELECT summary FROM group_ai_summaries WHERE chat_id=?",
                (int(chat_id),),
            ).fetchone()
            return (row[0] or "") if row else ""
        finally:
            conn.close()
    except Exception:
        return ""


def set_summary(chat_id: int, summary: str) -> None:
    summary = _clean(summary, 2000)
    if not summary:
        return
    _ensure_tables()
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO group_ai_summaries(chat_id,summary,updated_at) VALUES(?,?,?) "
            "ON CONFLICT(chat_id) DO UPDATE SET summary=excluded.summary,updated_at=excluded.updated_at",
            (int(chat_id), summary, int(time.time())),
        )
        conn.commit()
    finally:
        conn.close()


async def summarize_group(chat_id: int, user_id: int = 0) -> str:
    context = get_context(chat_id, max_turns=16, for_prompt=False)
    if not context or len(context) < 40:
        return "هنوز گفتگوی کافی برای خلاصه نیست."
    from bot.services.ai_service import ask_ai

    prompt = (
        "گفتگوی زیر از یک گروه تلگرام است. به فارسی در ۵ تا ۸ خط خلاصه کن:\n"
        "- موضوعات اصلی\n- تصمیم‌ها یا توافق‌ها\n- سؤال‌های باز\n"
        "حدس نزن و نام‌ها را جابه‌جا نکن.\n\n" + context[-5000:]
    )
    result = await ask_ai(int(user_id or 0), prompt)
    if isinstance(result, tuple):
        result = result[0]
    summary = str(result or "").strip()
    if summary:
        set_summary(chat_id, summary[:2000])
        return summary
    return "خلاصه‌سازی انجام نشد."
