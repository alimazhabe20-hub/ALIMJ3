"""امکانات اجتماعی اختصاصی هر گروه: دستیار، نظرسنجی، بازی، امتیاز، خوشامد و پنل."""
from __future__ import annotations

import html
import random
import re
import time
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatType
from telegram.ext import ContextTypes

from bot.database_core import get_db_connection
from bot.logger import logger


def _is_group(chat) -> bool:
    return bool(chat and chat.type in (ChatType.GROUP, ChatType.SUPERGROUP))


def ensure_group_community_tables() -> None:
    conn = get_db_connection()
    try:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS group_community (
            chat_id INTEGER PRIMARY KEY,
            assistant_name TEXT NOT NULL DEFAULT 'روز زیبا',
            assistant_prompt TEXT NOT NULL DEFAULT '',
            welcome_text TEXT NOT NULL DEFAULT 'سلام {name}، به {title} خوش اومدی! 🌷',
            welcome_enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS group_member_xp (
            chat_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            username TEXT DEFAULT '',
            display_name TEXT DEFAULT '',
            xp INTEGER NOT NULL DEFAULT 0,
            messages INTEGER NOT NULL DEFAULT 0,
            last_award REAL NOT NULL DEFAULT 0,
            PRIMARY KEY(chat_id, user_id)
        );
        CREATE INDEX IF NOT EXISTS idx_group_member_xp_rank
            ON group_member_xp(chat_id, xp DESC);
        CREATE TABLE IF NOT EXISTS group_community_polls (
            poll_id TEXT PRIMARY KEY,
            chat_id INTEGER NOT NULL,
            correct_option_id INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS group_poll_awards (
            poll_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            awarded_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY(poll_id, user_id)
        );
        """)
        conn.commit()
    finally:
        conn.close()


def _profile(chat_id: int) -> dict:
    ensure_group_community_tables()
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT assistant_name, assistant_prompt, welcome_text, welcome_enabled "
            "FROM group_community WHERE chat_id=?", (int(chat_id),)
        ).fetchone()
        if not row:
            return {"assistant_name": "روز زیبا", "assistant_prompt": "", "welcome_text": "سلام {name}، به {title} خوش اومدی! 🌷", "welcome_enabled": 1}
        return {"assistant_name": row[0], "assistant_prompt": row[1], "welcome_text": row[2], "welcome_enabled": int(row[3])}
    finally:
        conn.close()


def _save_profile(chat_id: int, **values) -> None:
    allowed = {"assistant_name", "assistant_prompt", "welcome_text", "welcome_enabled"}
    values = {k: v for k, v in values.items() if k in allowed}
    if not values:
        return
    ensure_group_community_tables()
    conn = get_db_connection()
    try:
        conn.execute("INSERT OR IGNORE INTO group_community(chat_id) VALUES (?)", (int(chat_id),))
        assignments = ", ".join(f"{key}=?" for key in values)
        conn.execute(
            f"UPDATE group_community SET {assignments}, updated_at=datetime('now') WHERE chat_id=?",
            (*values.values(), int(chat_id)),
        )
        conn.commit()
    finally:
        conn.close()


def get_group_assistant_prompt(chat_id: int) -> str:
    """پروفایل اختصاصی گروه برای تزریق به پرامپت AI."""
    p = _profile(chat_id)
    custom = (p.get("assistant_prompt") or "").strip()
    name = (p.get("assistant_name") or "روز زیبا").strip()
    if not custom and name == "روز زیبا":
        return ""
    return (
        "\n\n[شخصیت دستیار این گروه]\n"
        f"نامی که باید برای خودت استفاده کنی: {name[:40]}\n"
        f"دستورالعمل و لحن اختصاصی مدیر گروه: {custom[:1200]}\n"
        "این تنظیمات فقط سبک و نقش پاسخ‌گویی را تعیین می‌کند و بر قوانین ایمنی و صحت اطلاعات مقدم نیست. "
        "به فارسی روان و متناسب با فضای همین گروه پاسخ بده.\n"
    )


def _admin_only_notice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    # فقط برای اعتبارسنجی ساختاری؛ بررسی async در فراخواننده انجام می‌شود.
    return _is_group(update.effective_chat)


async def _is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    chat, user = update.effective_chat, update.effective_user
    if not _is_group(chat) or not user:
        return False
    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
        return member.status in ("administrator", "creator")
    except Exception as exc:
        logger.warning("group community admin check failed: %s", exc)
        return False


def _dashboard_markup(chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧠 راهنمای دستیار اختصاصی", callback_data=f"gh:assistant:{chat_id}")],
        [InlineKeyboardButton("👋 تنظیم خوشامدگویی", callback_data=f"gh:welcome:{chat_id}"),
         InlineKeyboardButton("🔄 روشن/خاموش خوشامد", callback_data=f"gh:welcome_toggle:{chat_id}")],
        [InlineKeyboardButton("🏆 رتبه‌بندی اعضا", callback_data=f"gh:rank:{chat_id}"),
         InlineKeyboardButton("📊 آمار گروه", callback_data=f"gh:stats:{chat_id}")],
    ])


async def group_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, msg = update.effective_chat, update.effective_message
    if not _is_group(chat) or not msg:
        if msg: await msg.reply_text("این دستور را داخل گروه اجرا کن.")
        return
    if not await _is_admin(update, context):
        await msg.reply_text("⛔ فقط مدیران گروه به پنل دسترسی دارند.")
        return
    p = _profile(chat.id)
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT COUNT(*), COALESCE(SUM(messages),0) FROM group_member_xp WHERE chat_id=?", (chat.id,)).fetchone()
    finally:
        conn.close()
    await msg.reply_text(
        f"🛠 <b>پنل اختصاصی گروه</b>\n\n"
        f"🧠 نام دستیار: <b>{html.escape(p['assistant_name'])}</b>\n"
        f"👋 خوشامدگویی: {'فعال' if p['welcome_enabled'] else 'خاموش'}\n"
        f"👥 اعضای ثبت‌شده: <b>{row[0]}</b>\n💬 پیام‌های ثبت‌شده: <b>{row[1]}</b>\n\n"
        "برای تنظیم دستیار و خوشامد از دکمه‌ها یا دستورهای راهنما استفاده کن.",
        parse_mode="HTML", reply_markup=_dashboard_markup(chat.id),
    )


async def set_group_assistant_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, msg = update.effective_chat, update.effective_message
    if not _is_group(chat) or not msg: return
    if not await _is_admin(update, context):
        await msg.reply_text("⛔ فقط مدیر گروه می‌تواند دستیار را تنظیم کند."); return
    raw = " ".join(context.args or []).strip()
    if not raw:
        await msg.reply_text("روش استفاده:\n/setassistant نام دستیار | شخصیت و دستورالعمل\nمثال:\n/setassistant مشاور گروه | صمیمی، دقیق و کوتاه جواب بده و اعضا را با احترام خطاب کن.")
        return
    if "|" in raw:
        name, prompt = raw.split("|", 1)
    else:
        name, prompt = "دستیار گروه", raw
    _save_profile(chat.id, assistant_name=name.strip()[:40] or "دستیار گروه", assistant_prompt=prompt.strip()[:1200])
    await msg.reply_text("✅ شخصیت اختصاصی دستیار این گروه ذخیره شد. از این به بعد پاسخ‌های هوش مصنوعی با این تنظیمات هماهنگ می‌شوند.")


async def set_group_welcome_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, msg = update.effective_chat, update.effective_message
    if not _is_group(chat) or not msg: return
    if not await _is_admin(update, context):
        await msg.reply_text("⛔ فقط مدیر گروه می‌تواند خوشامدگویی را تنظیم کند."); return
    raw = " ".join(context.args or []).strip()
    if not raw:
        await msg.reply_text("روش استفاده:\n/setwelcome متن خوشامدگویی\nمتغیرها: {name} نام عضو، {title} نام گروه، {username} نام کاربری")
        return
    _save_profile(chat.id, welcome_text=raw[:900], welcome_enabled=1)
    await msg.reply_text("✅ متن خوشامدگویی ذخیره و فعال شد.")


async def welcome_toggle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, msg = update.effective_chat, update.effective_message
    if not _is_group(chat) or not msg: return
    if not await _is_admin(update, context):
        await msg.reply_text("⛔ فقط مدیر گروه می‌تواند این تنظیم را تغییر دهد."); return
    p = _profile(chat.id)
    enabled = 0 if p["welcome_enabled"] else 1
    _save_profile(chat.id, welcome_enabled=enabled)
    await msg.reply_text("👋 خوشامدگویی " + ("فعال شد." if enabled else "خاموش شد."))


async def group_member_join_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    msg = update.effective_message
    if not _is_group(chat) or not msg or not msg.new_chat_members:
        return
    p = _profile(chat.id)
    if not p["welcome_enabled"]: return
    for member in msg.new_chat_members[:10]:
        if member.is_bot: continue
        name = html.escape(member.full_name or member.first_name or "دوست جدید")
        username = html.escape("@" + member.username if member.username else "")
        title = html.escape(chat.title or "گروه")
        text = p["welcome_text"] or "سلام {name}، به {title} خوش اومدی! 🌷"
        text = text.replace("{name}", name).replace("{title}", title).replace("{username}", username)
        try:
            await msg.reply_text(text[:1000], parse_mode="HTML", disable_web_page_preview=True)
        except Exception as exc:
            logger.warning("group welcome send failed: %s", exc)


async def group_activity_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ثبت فعالیت و XP؛ هر عضو حداکثر هر 60 ثانیه XP فعالیت می‌گیرد."""
    msg, chat, user = update.effective_message, update.effective_chat, update.effective_user
    if not msg or not _is_group(chat) or not user or user.is_bot or msg.new_chat_members:
        return
    ensure_group_community_tables()
    now = time.time()
    name = (user.full_name or user.first_name or "کاربر")[:80]
    username = (user.username or "")[:64]
    conn = get_db_connection()
    try:
        conn.execute("""INSERT OR IGNORE INTO group_member_xp
            (chat_id,user_id,username,display_name,xp,messages,last_award)
            VALUES (?,?,?,?,0,0,0)""", (chat.id, user.id, username, name))
        conn.execute("""UPDATE group_member_xp SET username=?, display_name=?, messages=messages+1,
            xp=xp + CASE WHEN ? - last_award >= 60 THEN 2 ELSE 0 END,
            last_award=CASE WHEN ? - last_award >= 60 THEN ? ELSE last_award END
            WHERE chat_id=? AND user_id=?""", (username, name, now, now, now, chat.id, user.id))
        conn.commit()
    except Exception as exc:
        logger.warning("group XP tracking failed: %s", exc)
    finally:
        conn.close()


def _level(xp: int) -> int:
    return max(1, int((max(0, xp) / 100) ** 0.5) + 1)


async def rank_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, msg = update.effective_chat, update.effective_message
    if not _is_group(chat) or not msg: return
    ensure_group_community_tables()
    conn = get_db_connection()
    try:
        rows = conn.execute("SELECT user_id,display_name,xp,messages FROM group_member_xp WHERE chat_id=? ORDER BY xp DESC, messages DESC LIMIT 10", (chat.id,)).fetchall()
        mine = conn.execute("SELECT xp,messages FROM group_member_xp WHERE chat_id=? AND user_id=?", (chat.id, update.effective_user.id)).fetchone()
    finally: conn.close()
    if not rows:
        await msg.reply_text("هنوز امتیازی ثبت نشده؛ با مشارکت در گفتگو امتیاز جمع کن!"); return
    medals = ["🥇", "🥈", "🥉"]
    lines = ["🏆 <b>جدول امتیاز اعضای گروه</b>"]
    for i, row in enumerate(rows, 1):
        lines.append(f"{medals[i-1] if i <= 3 else str(i)+'.'} {html.escape(row[1] or 'عضو')} — <b>{row[2]} XP</b> · سطح { _level(row[2]) }")
    if mine:
        lines.append(f"\n⭐ امتیاز شما: {mine[0]} · سطح {_level(mine[0])} · {mine[1]} پیام")
    lines.append("\nهر ۶۰ ثانیه فعالیت مفید: ۲ امتیاز")
    await msg.reply_text("\n".join(lines), parse_mode="HTML")


async def poll_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, msg = update.effective_chat, update.effective_message
    if not _is_group(chat) or not msg: return
    raw = " ".join(context.args or [])
    parts = [p.strip() for p in raw.split("|") if p.strip()]
    if len(parts) < 3:
        await msg.reply_text("روش ساخت نظرسنجی:\n/poll موضوع | گزینه اول | گزینه دوم | گزینه سوم\nحداقل دو گزینه لازم است."); return
    question, options = parts[0][:300], parts[1:11]
    try:
        sent = await context.bot.send_poll(chat_id=chat.id, question=question, options=options, is_anonymous=False, allows_multiple_answers=False)
        if sent.poll:
            ensure_group_community_tables()
            conn = get_db_connection()
            try:
                conn.execute("INSERT OR REPLACE INTO group_community_polls(poll_id,chat_id,correct_option_id) VALUES(?,?,NULL)", (sent.poll.id, chat.id))
                conn.commit()
            finally: conn.close()
    except Exception as exc:
        logger.warning("group poll failed: %s", exc)
        await msg.reply_text("⚠️ ساخت نظرسنجی ممکن نشد. دسترسی ارسال نظرسنجی ربات را بررسی کن.")


async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, msg = update.effective_chat, update.effective_message
    if not _is_group(chat) or not msg: return
    raw = " ".join(context.args or [])
    parts = [p.strip() for p in raw.split("|") if p.strip()]
    if len(parts) < 4:
        await msg.reply_text("روش مسابقه:\n/quiz سؤال | گزینه ۱ | گزینه ۲ | شماره پاسخ صحیح\nشماره پاسخ از ۱ شروع می‌شود."); return
    question, options = parts[0][:280], parts[1:-1][:10]
    try: correct = int(parts[-1]) - 1
    except ValueError: correct = -1
    if len(options) < 2 or not 0 <= correct < len(options):
        await msg.reply_text("⚠️ شماره پاسخ صحیح معتبر نیست."); return
    try:
        sent = await context.bot.send_poll(chat_id=chat.id, question=question, options=options, type="quiz", correct_option_id=correct, is_anonymous=False, explanation="آفرین به شرکت‌کنندگان! برای دیدن رتبه خود /rank را بزنید.")
        if sent.poll:
            ensure_group_community_tables()
            conn = get_db_connection()
            try:
                conn.execute("INSERT OR REPLACE INTO group_community_polls(poll_id,chat_id,correct_option_id) VALUES(?,?,?)", (sent.poll.id, chat.id, correct))
                conn.commit()
            finally: conn.close()
    except Exception as exc:
        logger.warning("group quiz failed: %s", exc)
        await msg.reply_text("⚠️ ساخت مسابقه ممکن نشد. نسخه تلگرام و دسترسی‌های ربات را بررسی کن.")


async def group_poll_answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """برای رأی‌دهی امتیاز می‌دهد؛ هر عضو برای هر نظرسنجی فقط یک بار."""
    answer = getattr(update, "poll_answer", None)
    if not answer or not answer.user:
        return
    ensure_group_community_tables()
    conn = get_db_connection()
    try:
        poll = conn.execute("SELECT chat_id,correct_option_id FROM group_community_polls WHERE poll_id=?", (answer.poll_id,)).fetchone()
        if not poll:
            return
        chat_id, correct_option = int(poll[0]), poll[1]
        cur = conn.execute("INSERT OR IGNORE INTO group_poll_awards(poll_id,user_id) VALUES(?,?)", (answer.poll_id, answer.user.id))
        if cur.rowcount == 0:
            return
        points = 2
        if correct_option is not None:
            points = 10 if list(answer.option_ids or []) == [int(correct_option)] else 1
        name = (answer.user.full_name or answer.user.first_name or "کاربر")[:80]
        username = (answer.user.username or "")[:64]
        conn.execute("""INSERT INTO group_member_xp(chat_id,user_id,username,display_name,xp,messages,last_award)
            VALUES(?,?,?,?,?,0,?) ON CONFLICT(chat_id,user_id) DO UPDATE SET
            username=excluded.username,display_name=excluded.display_name,xp=group_member_xp.xp+excluded.xp""",
            (chat_id, answer.user.id, username, name, points, time.time()))
        conn.commit()
    except Exception as exc:
        logger.warning("group poll answer award failed: %s", exc)
    finally:
        conn.close()


async def game_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, msg = update.effective_chat, update.effective_message
    if not _is_group(chat) or not msg: return
    game = (context.args[0].lower() if context.args else "dice")
    if game in ("dice", "تاس", "🎲"):
        try:
            result = await context.bot.send_dice(chat_id=chat.id, emoji="🎲")
            value = result.dice.value if result.dice else 0
            await msg.reply_text(f"🎲 نتیجه تاس: {value} از ۶ — برای رقابت، هر نفر /game dice را بزند!")
        except Exception as exc:
            logger.warning("group dice failed: %s", exc)
            await msg.reply_text("⚠️ اجرای بازی ممکن نشد.")
    elif game in ("quiz", "مسابقه"):
        await msg.reply_text("🧠 برای مسابقه دانستنی‌ها از دستور /quiz سؤال | گزینه ۱ | گزینه ۲ | شماره پاسخ صحیح استفاده کن.")
    else:
        await msg.reply_text("بازی‌های فعلی: /game dice و /game quiz")


async def group_community_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q: return
    data = q.data or ""
    try:
        _, action, chat_s = data.split(":", 2)
        chat_id = int(chat_s)
    except Exception:
        await q.answer(); return
    if not update.effective_chat or update.effective_chat.id != chat_id:
        await q.answer("این پنل متعلق به گروه دیگری است.", show_alert=True); return
    if not await _is_admin(update, context):
        await q.answer("فقط مدیران گروه دسترسی دارند.", show_alert=True); return
    p = _profile(chat_id)
    if action == "assistant":
        text = "🧠 <b>دستیار اختصاصی گروه</b>\nبرای تغییر نام و شخصیت:\n<code>/setassistant نام | دستورالعمل</code>\nمثال: <code>/setassistant مشاور | صمیمی، دقیق و مختصر جواب بده.</code>"
    elif action == "welcome_toggle":
        enabled = 0 if p["welcome_enabled"] else 1
        _save_profile(chat_id, welcome_enabled=enabled)
        text = "👋 خوشامدگویی " + ("فعال شد." if enabled else "خاموش شد.")
    elif action == "welcome":
        text = "👋 <b>خوشامدگویی شخصی‌سازی‌شده</b>\nمتن: <code>/setwelcome سلام {name}، به {title} خوش اومدی!</code>\nفعال/خاموش: <code>/welcometoggle</code>\nمتغیرها: {name}، {title}، {username}\nوضعیت: " + ("فعال" if p["welcome_enabled"] else "خاموش")
    elif action == "rank":
        conn = get_db_connection()
        try: rows = conn.execute("SELECT display_name,xp FROM group_member_xp WHERE chat_id=? ORDER BY xp DESC LIMIT 5", (chat_id,)).fetchall()
        finally: conn.close()
        text = "🏆 <b>۵ عضو برتر</b>\n" + ("\n".join(f"{i}. {html.escape(r[0] or 'عضو')} — {r[1]} XP" for i, r in enumerate(rows, 1)) if rows else "هنوز امتیازی ثبت نشده است.")
    elif action == "stats":
        conn = get_db_connection()
        try: row = conn.execute("SELECT COUNT(*),COALESCE(SUM(messages),0),COALESCE(SUM(xp),0) FROM group_member_xp WHERE chat_id=?", (chat_id,)).fetchone()
        finally: conn.close()
        text = f"📊 <b>آمار گروه</b>\nاعضای ثبت‌شده: {row[0]}\nپیام‌های شمارش‌شده: {row[1]}\nمجموع امتیازها: {row[2]}"
    else:
        await q.answer(); return
    await q.answer()
    await q.message.reply_text(text, parse_mode="HTML")
