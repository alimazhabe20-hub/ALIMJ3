"""Advanced per-group dashboard, missions and analytics for ALIMJ3."""
from __future__ import annotations

import html
import time
from datetime import date, timedelta
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatType
from telegram.ext import ContextTypes

from bot.database_core import get_db_connection
from bot.logger import logger

_METRICS = {"messages", "replies", "media"}
_TABLES_READY = False
_SEEDED_PERIODS: set[tuple[int, str, str]] = set()


def _is_group(chat) -> bool:
    return bool(chat and chat.type in (ChatType.GROUP, ChatType.SUPERGROUP))


def ensure_group_advanced_tables() -> None:
    global _TABLES_READY
    if _TABLES_READY:
        return
    conn = get_db_connection()
    try:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS group_daily_stats (
            chat_id INTEGER NOT NULL,
            day TEXT NOT NULL,
            messages INTEGER NOT NULL DEFAULT 0,
            media INTEGER NOT NULL DEFAULT 0,
            replies INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(chat_id, day)
        );
        CREATE TABLE IF NOT EXISTS group_daily_users (
            chat_id INTEGER NOT NULL,
            day TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            message_count INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(chat_id, day, user_id)
        );
        CREATE INDEX IF NOT EXISTS idx_group_daily_stats_day
            ON group_daily_stats(chat_id, day);
        CREATE TABLE IF NOT EXISTS group_missions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            mission_key TEXT NOT NULL,
            period_key TEXT NOT NULL,
            title TEXT NOT NULL,
            metric TEXT NOT NULL,
            target INTEGER NOT NULL,
            reward_xp INTEGER NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 1,
            created_at INTEGER NOT NULL,
            UNIQUE(chat_id, mission_key, period_key)
        );
        CREATE TABLE IF NOT EXISTS group_mission_progress (
            mission_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            progress INTEGER NOT NULL DEFAULT 0,
            claimed INTEGER NOT NULL DEFAULT 0,
            updated_at INTEGER NOT NULL,
            PRIMARY KEY(mission_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS group_mission_event_buckets (
            chat_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            metric TEXT NOT NULL,
            bucket INTEGER NOT NULL,
            PRIMARY KEY(chat_id, user_id, metric, bucket)
        );
        """)
        conn.commit()
        _TABLES_READY = True
    finally:
        conn.close()


def _period_keys():
    today = date.today()
    iso = today.isocalendar()
    return today.isoformat(), f"{iso.year}-W{iso.week:02d}"


def _ensure_default_missions(chat_id: int) -> None:
    ensure_group_advanced_tables()
    day_key, week_key = _period_keys()
    cache_key = (int(chat_id), day_key, week_key)
    if cache_key in _SEEDED_PERIODS:
        return
    now = int(time.time())
    defaults = [
        ("daily_messages", day_key, "امروز ۵ پیام مفید بفرست", "messages", 5, 20),
        ("daily_replies", day_key, "امروز به ۲ پیام پاسخ بده", "replies", 2, 15),
        ("daily_media", day_key, "امروز یک عکس یا رسانه به اشتراک بگذار", "media", 1, 10),
        ("weekly_messages", week_key, "این هفته ۲۵ پیام در گفتگو مشارکت کن", "messages", 25, 80),
    ]
    conn = get_db_connection()
    try:
        conn.executemany(
            """INSERT OR IGNORE INTO group_missions
            (chat_id,mission_key,period_key,title,metric,target,reward_xp,enabled,created_at)
            VALUES(?,?,?,?,?,?,?,1,?)""",
            [(chat_id, *item, now) for item in defaults],
        )
        conn.commit()
        _SEEDED_PERIODS.add(cache_key)
    finally:
        conn.close()


def _user_name(user) -> str:
    return (getattr(user, "full_name", None) or getattr(user, "first_name", None) or "عضو")[:80]


async def _is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Share the canonical admin check, including configured bot administrators."""
    if not _is_group(update.effective_chat) or not update.effective_user:
        return False
    try:
        from bot.handlers.group_mode import user_is_group_admin
        return await user_is_group_admin(update, context)
    except Exception as exc:
        logger.warning("group advanced admin check failed: %s", exc, exc_info=True)
        return False


def _dashboard(chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 گزارش هفتگی", callback_data=f"ga:stats:{chat_id}")],
        [InlineKeyboardButton("🎯 مأموریت‌ها", callback_data=f"ga:missions:{chat_id}")],
        [InlineKeyboardButton("🏆 رتبه اعضا", callback_data=f"ga:rank:{chat_id}")],
        [InlineKeyboardButton("📖 راهنمای مدیریت", callback_data=f"ga:help:{chat_id}")],
    ])


async def group_control_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, msg = update.effective_chat, update.effective_message
    if not _is_group(chat) or not msg:
        if msg:
            await msg.reply_text("این دستور فقط داخل گروه قابل استفاده است.")
        return
    if not await _is_admin(update, context):
        await msg.reply_text("⛔ پنل پیشرفته فقط برای مدیران گروه است.")
        return
    ensure_group_advanced_tables()
    _ensure_default_missions(chat.id)
    conn = get_db_connection()
    try:
        today = date.today().isoformat()
        row = conn.execute(
            "SELECT messages,media,replies FROM group_daily_stats WHERE chat_id=? AND day=?",
            (chat.id, today),
        ).fetchone() or (0, 0, 0)
        users = conn.execute(
            "SELECT COUNT(*) FROM group_daily_users WHERE chat_id=? AND day=?",
            (chat.id, today),
        ).fetchone()[0]
        missions = conn.execute(
            "SELECT COUNT(*) FROM group_missions WHERE chat_id=? AND enabled=1",
            (chat.id,),
        ).fetchone()[0]
    finally:
        conn.close()
    await msg.reply_text(
        "🛠 <b>مرکز مدیریت پیشرفته گروه</b>\n\n"
        f"📨 پیام‌های امروز: <b>{row[0]}</b>\n"
        f"👥 اعضای فعال امروز: <b>{users}</b>\n"
        f"🖼 رسانه‌ها: <b>{row[1]}</b>  ·  ↩️ پاسخ‌ها: <b>{row[2]}</b>\n"
        f"🎯 مأموریت‌های فعال: <b>{missions}</b>\n\n"
        "از دکمه‌های زیر برای گزارش، مأموریت‌ها و رتبه‌بندی استفاده کن.",
        parse_mode="HTML",
        reply_markup=_dashboard(chat.id),
    )


def _record_metric(conn, chat_id: int, user_id: int, metric: str, now: int) -> None:
    """Progress each metric at most once per 30-second bucket to reduce spam farming."""
    if metric not in _METRICS:
        return
    bucket = now // 30
    cur = conn.execute(
        "INSERT OR IGNORE INTO group_mission_event_buckets(chat_id,user_id,metric,bucket) VALUES(?,?,?,?)",
        (chat_id, user_id, metric, bucket),
    )
    if cur.rowcount == 0:
        return
    missions = conn.execute(
        """SELECT id FROM group_missions
        WHERE chat_id=? AND metric=? AND enabled=1
        AND ((mission_key LIKE 'daily_%' AND period_key=?) OR
             (mission_key LIKE 'weekly_%' AND period_key=?) OR
             mission_key LIKE 'custom_%')""",
        (chat_id, metric, date.today().isoformat(), _period_keys()[1]),
    ).fetchall()
    for (mission_id,) in missions:
        conn.execute(
            """INSERT INTO group_mission_progress(mission_id,user_id,progress,claimed,updated_at)
            VALUES(?,?,1,0,?) ON CONFLICT(mission_id,user_id)
            DO UPDATE SET progress=MIN(group_mission_progress.progress+1,
                (SELECT target FROM group_missions WHERE id=?)), updated_at=excluded.updated_at""",
            (mission_id, user_id, now, mission_id),
        )


async def group_advanced_activity_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Collect group analytics and mission progress; never blocks normal handlers."""
    msg, chat, user = update.effective_message, update.effective_chat, update.effective_user
    if not msg or not _is_group(chat) or not user or user.is_bot:
        return
    if msg.new_chat_members or msg.left_chat_member:
        return
    try:
        ensure_group_advanced_tables()
        day = date.today().isoformat()
        now = int(time.time())
        is_media = bool(msg.photo or msg.video or msg.document or msg.audio or msg.voice or msg.animation)
        is_reply = bool(msg.reply_to_message)
        _ensure_default_missions(chat.id)
        conn = get_db_connection()
        try:
            conn.execute(
                """INSERT INTO group_daily_stats(chat_id,day,messages,media,replies)
                VALUES(?,?,1,?,?) ON CONFLICT(chat_id,day) DO UPDATE SET
                messages=messages+1, media=media+excluded.media, replies=replies+excluded.replies""",
                (chat.id, day, int(is_media), int(is_reply)),
            )
            conn.execute(
                """INSERT INTO group_daily_users(chat_id,day,user_id,message_count)
                VALUES(?,?,?,1) ON CONFLICT(chat_id,day,user_id)
                DO UPDATE SET message_count=message_count+1""",
                (chat.id, day, user.id),
            )
            _record_metric(conn, chat.id, user.id, "messages", now)
            if is_media:
                _record_metric(conn, chat.id, user.id, "media", now)
            if is_reply:
                _record_metric(conn, chat.id, user.id, "replies", now)
            # Bound dedup-bucket retention.
            conn.execute("DELETE FROM group_mission_event_buckets WHERE bucket < ?", (now // 30 - 60 * 24 * 14,))
            conn.commit()
        finally:
            conn.close()
    except Exception as exc:
        logger.warning("group advanced activity tracking failed: %s", exc)


def _mission_rows(chat_id: int, user_id: int):
    _ensure_default_missions(chat_id)
    conn = get_db_connection()
    try:
        return conn.execute(
            """SELECT m.id,m.title,m.metric,m.target,m.reward_xp,
            COALESCE(p.progress,0),COALESCE(p.claimed,0),m.period_key
            FROM group_missions m LEFT JOIN group_mission_progress p
            ON p.mission_id=m.id AND p.user_id=?
            WHERE m.chat_id=? AND m.enabled=1
            ORDER BY CASE WHEN m.mission_key LIKE 'daily_%' THEN 0 ELSE 1 END,m.id""",
            (user_id, chat_id),
        ).fetchall()
    finally:
        conn.close()


def _missions_text(rows, user_name: str = "") -> str:
    lines = ["🎯 <b>مأموریت‌های گروه</b>"]
    for row in rows:
        mission_id, title, metric, target, reward, progress, claimed, period_key = row
        period = "هفتگی" if "-W" in period_key else ("سفارشی" if period_key == "custom" else "روزانه")
        status = "✅ جایزه دریافت شد" if claimed else ("🎁 آماده دریافت" if progress >= target else f"{progress}/{target}")
        lines.append(
            f"\n<b>{html.escape(title)}</b> · {period}\n"
            f"پیشرفت: <b>{min(progress, target)}/{target}</b> · جایزه: <b>{reward} XP</b>\n"
            f"وضعیت: {status}"
        )
    if len(lines) == 1:
        lines.append("فعلاً مأموریتی فعال نیست.")
    return "\n".join(lines)


def _mission_keyboard(chat_id: int, rows) -> Optional[InlineKeyboardMarkup]:
    buttons = []
    for row in rows:
        mission_id, title, metric, target, reward, progress, claimed, period_key = row
        if progress >= target and not claimed:
            buttons.append([InlineKeyboardButton(
                f"🎁 دریافت {reward} XP · {title[:22]}",
                callback_data=f"ga:claim:{chat_id}:{mission_id}",
            )])
    buttons.append([InlineKeyboardButton("🔄 به‌روزرسانی", callback_data=f"ga:missions:{chat_id}")])
    return InlineKeyboardMarkup(buttons)


async def missions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, msg, user = update.effective_chat, update.effective_message, update.effective_user
    if not _is_group(chat) or not msg or not user:
        return
    rows = _mission_rows(chat.id, user.id)
    await msg.reply_text(_missions_text(rows), parse_mode="HTML", reply_markup=_mission_keyboard(chat.id, rows))


def _stats_text(chat_id: int, days: int = 7) -> str:
    ensure_group_advanced_tables()
    try:
        from bot.handlers.group_community import ensure_group_community_tables
        ensure_group_community_tables()
    except Exception as exc:
        logger.debug("group community tables unavailable for stats: %s", exc)
    start = (date.today() - timedelta(days=days - 1)).isoformat()
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """SELECT day,messages,media,replies FROM group_daily_stats
            WHERE chat_id=? AND day>=? ORDER BY day DESC LIMIT ?""",
            (chat_id, start, days),
        ).fetchall()
        total = conn.execute(
            """SELECT COALESCE(SUM(messages),0),COALESCE(SUM(media),0),
            COALESCE(SUM(replies),0) FROM group_daily_stats WHERE chat_id=? AND day>=?""",
            (chat_id, start),
        ).fetchone()
        active = conn.execute(
            "SELECT COUNT(DISTINCT user_id) FROM group_daily_users WHERE chat_id=? AND day>=?",
            (chat_id, start),
        ).fetchone()[0]
        top = conn.execute(
            """SELECT x.display_name,SUM(d.message_count) AS n
            FROM group_daily_users d LEFT JOIN group_member_xp x
            ON x.chat_id=d.chat_id AND x.user_id=d.user_id
            WHERE d.chat_id=? AND d.day>=?
            GROUP BY d.user_id ORDER BY n DESC LIMIT 5""",
            (chat_id, start),
        ).fetchall()
    finally:
        conn.close()
    lines = [
        f"📊 <b>گزارش {days} روز اخیر گروه</b>",
        f"💬 مجموع پیام‌ها: <b>{total[0]}</b>",
        f"🖼 رسانه‌ها: <b>{total[1]}</b>",
        f"↩️ پاسخ‌ها: <b>{total[2]}</b>",
        f"👥 اعضای فعال یکتا: <b>{active}</b>",
        "\n<b>فعالیت روزانه</b>",
    ]
    lines.extend(f"• {day}: {count} پیام" for day, count, media, replies in rows)
    lines.append("\n<b>اعضای فعال‌تر</b>")
    lines.extend(f"• {html.escape(name or 'عضو')}: {count} پیام" for name, count in top)
    if not rows:
        lines.append("هنوز داده‌ای برای این بازه ثبت نشده است.")
    return "\n".join(lines)


async def group_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, msg = update.effective_chat, update.effective_message
    if not _is_group(chat) or not msg:
        return
    days = 30 if context.args and context.args[0] in ("30", "ماه", "ماهانه") else 7
    if not await _is_admin(update, context):
        await msg.reply_text("⛔ گزارش آماری فقط برای مدیران گروه است.")
        return
    await msg.reply_text(_stats_text(chat.id, days), parse_mode="HTML")


async def mission_create_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, msg = update.effective_chat, update.effective_message
    if not _is_group(chat) or not msg:
        return
    if not await _is_admin(update, context):
        await msg.reply_text("⛔ فقط مدیر گروه می‌تواند مأموریت بسازد.")
        return
    raw = " ".join(context.args or []).strip()
    parts = [p.strip() for p in raw.split("|")]
    if len(parts) < 4:
        await msg.reply_text(
            "روش ساخت مأموریت:\n"
            "/missioncreate messages|عنوان مأموریت|هدف عددی|جایزه XP\n"
            "نوع‌های پشتیبانی‌شده: messages، replies، media"
        )
        return
    metric, title = parts[0].lower(), parts[1][:100]
    if metric not in _METRICS:
        await msg.reply_text("نوع مأموریت باید messages یا replies یا media باشد.")
        return
    try:
        target, reward = int(parts[2]), int(parts[3])
    except ValueError:
        await msg.reply_text("هدف و جایزه باید عدد باشند.")
        return
    if not (1 <= target <= 500 and 1 <= reward <= 5000):
        await msg.reply_text("هدف باید بین ۱ تا ۵۰۰ و جایزه بین ۱ تا ۵۰۰۰ XP باشد.")
        return
    ensure_group_advanced_tables()
    key = f"custom_{int(time.time())}"
    conn = get_db_connection()
    try:
        conn.execute(
            """INSERT INTO group_missions(chat_id,mission_key,period_key,title,metric,target,reward_xp,enabled,created_at)
            VALUES(?,?,?,?,?,?,?,1,?)""",
            (chat.id, key, "custom", title, metric, target, reward, int(time.time())),
        )
        conn.commit()
    finally:
        conn.close()
    await msg.reply_text(f"✅ مأموریت «{html.escape(title)}» ساخته شد؛ برای مشاهده /missions را بزن.", parse_mode="HTML")


async def group_advanced_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q:
        return
    data = q.data or ""
    parts = data.split(":")
    if len(parts) < 3 or parts[0] != "ga":
        await q.answer()
        return
    action = parts[1]
    try:
        chat_id = int(parts[2])
    except ValueError:
        await q.answer()
        return
    chat = update.effective_chat
    if not chat or chat.id != chat_id or not _is_group(chat):
        await q.answer("این دکمه متعلق به گروه دیگری است.", show_alert=True)
        return

    if action == "claim":
        if len(parts) != 4 or not update.effective_user:
            await q.answer("درخواست نامعتبر است.", show_alert=True)
            return
        try:
            mission_id = int(parts[3])
        except ValueError:
            await q.answer("درخواست نامعتبر است.", show_alert=True)
            return
        user = update.effective_user
        ensure_group_advanced_tables()
        try:
            # Existing XP table is created by the community module.
            from bot.handlers.group_community import ensure_group_community_tables
            ensure_group_community_tables()
            conn = get_db_connection()
            try:
                row = conn.execute(
                    """SELECT m.title,m.target,m.reward_xp,p.progress,p.claimed
                    FROM group_missions m JOIN group_mission_progress p ON p.mission_id=m.id
                    WHERE m.id=? AND m.chat_id=? AND p.user_id=? AND m.enabled=1""",
                    (mission_id, chat_id, user.id),
                ).fetchone()
                if not row:
                    await q.answer("مأموریت یا پیشرفت آن پیدا نشد.", show_alert=True)
                    return
                title, target, reward, progress, claimed = row
                if claimed:
                    await q.answer("جایزه قبلاً دریافت شده است.", show_alert=True)
                    return
                if progress < target:
                    await q.answer("هنوز مأموریت کامل نشده است.", show_alert=True)
                    return
                cur = conn.execute(
                    "UPDATE group_mission_progress SET claimed=1,updated_at=? WHERE mission_id=? AND user_id=? AND claimed=0 AND progress>=?",
                    (int(time.time()), mission_id, user.id, int(target)),
                )
                if cur.rowcount != 1:
                    await q.answer("جایزه قبلاً دریافت شده یا مأموریت کامل نیست.", show_alert=True)
                    return
                conn.execute(
                    """INSERT INTO group_member_xp(chat_id,user_id,username,display_name,xp,messages,last_award)
                    VALUES(?,?,?,?,?,0,?) ON CONFLICT(chat_id,user_id) DO UPDATE SET
                    xp=group_member_xp.xp+excluded.xp,username=excluded.username,display_name=excluded.display_name""",
                    (chat_id, user.id, user.username or "", _user_name(user), int(reward), time.time()),
                )
                conn.commit()
            finally:
                conn.close()
            await q.answer(f"{reward} XP دریافت کردی! 🎉", show_alert=True)
            rows = _mission_rows(chat_id, user.id)
            try:
                await q.edit_message_text(_missions_text(rows), parse_mode="HTML", reply_markup=_mission_keyboard(chat_id, rows))
            except Exception:
                pass
        except Exception as exc:
            logger.warning("group mission reward claim failed: %s", exc)
            await q.answer("دریافت جایزه انجام نشد؛ دوباره تلاش کن.", show_alert=True)
        return

    if action in ("stats", "missions", "rank", "help", "dashboard"):
        if action != "missions" and not await _is_admin(update, context):
            await q.answer("فقط مدیران گروه دسترسی دارند.", show_alert=True)
            return
        await q.answer()
        if action == "stats":
            await q.message.reply_text(_stats_text(chat_id, 7), parse_mode="HTML")
        elif action == "missions":
            rows = _mission_rows(chat_id, update.effective_user.id)
            await q.message.reply_text(_missions_text(rows), parse_mode="HTML", reply_markup=_mission_keyboard(chat_id, rows))
        elif action == "rank":
            try:
                from bot.handlers.group_community import rank_command
                # Use the already registered command output by directing admin to command.
                await q.message.reply_text("برای مشاهده جدول کامل رتبه‌بندی: /rank")
            except Exception:
                await q.message.reply_text("رتبه‌بندی در دسترس نیست.")
        elif action == "help":
            await q.message.reply_text(
                "📖 <b>راهنمای پنل پیشرفته</b>\n"
                "/groupstats — گزارش ۷ روز اخیر\n"
                "/groupstats 30 — گزارش ۳۰ روز اخیر\n"
                "/missions — مأموریت‌های فعال و دریافت جایزه\n"
                "/missioncreate messages|عنوان|هدف|XP — ساخت مأموریت\n"
                "نوع‌ها: messages، replies، media",
                parse_mode="HTML",
            )
        else:
            await q.message.reply_text(
                "🛠 <b>مرکز مدیریت پیشرفته گروه</b>\nاز دکمه‌های زیر استفاده کن.",
                parse_mode="HTML",
                reply_markup=_dashboard(chat_id),
            )
        return
    await q.answer()


async def mission_award_poll_placeholder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reserved for future poll-based missions; intentionally no-op."""
    return
