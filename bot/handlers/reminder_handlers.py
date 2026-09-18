"""Advanced personal reminder manager: list, pause/resume, edit and delete."""
from __future__ import annotations
from datetime import datetime
import pytz
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from bot.config import config
from bot.database import list_user_reminders, set_reminder_active, delete_reminder, update_reminder
from bot.services.ai_extras import parse_natural_reminder

def _tz():
    try: return pytz.timezone(getattr(config, "TIMEZONE", "Asia/Tehran"))
    except Exception: return pytz.timezone("Asia/Tehran")

def _fmt(iso):
    try:
        dt=datetime.fromisoformat(str(iso))
        if dt.tzinfo is None: dt=_tz().localize(dt)
        return dt.astimezone(_tz()).strftime("%Y/%m/%d • %H:%M")
    except Exception: return str(iso)

def _repeat(rt, every):
    return {"once":"یک‌بار", "daily":"روزانه", "weekly":"هفتگی", "monthly":"ماهانه", "every_minutes":f"هر {every} دقیقه", "every_hours":f"هر {every} ساعت"}.get(rt, rt or "یک‌بار")

def reminder_manager_text(user_id):
    rows=list_user_reminders(user_id, limit=30)
    active=[r for r in rows if int(r[6] or 0)==1 and int(r[5] or 0)==0]
    paused=[r for r in rows if int(r[6] or 0)==0]
    lines=["⏰ مدیریت حرفه‌ای یادآوری‌ها", "━━━━━━━━━━━━━━━━", f"🟢 فعال: {len(active)}   ⏸️ غیرفعال: {len(paused)}", ""]
    if not rows:
        lines += ["📭 هنوز هیچ یادآوری‌ای ثبت نشده.", "", "💡 برای ساخت یادآوری فقط بنویس:", "«یادآوری کن فردا ساعت ۹ قبض را پرداخت کنم»"]
    else:
        for i,r in enumerate(rows[:12],1):
            rid,text,when,rt,every,done,activeflag=r
            status="🟢" if int(activeflag or 0) and not int(done or 0) else "⏸️"
            lines.append(f"{status} {i}. {text}")
            lines.append(f"   🕐 {_fmt(when)}  •  🔁 {_repeat(rt,every)}")
    lines += ["", "⚙️ از دکمه‌های هر یادآوری برای توقف/فعال‌سازی، ویرایش یا حذف استفاده کن."]
    return "\n".join(lines), rows[:12]

def reminder_manager_keyboard(rows):
    kb=[]
    for r in rows:
        rid, text, when, rt, every, done, active = r
        label=("▶️" if not int(active or 0) else "⏸️") + " " + str(text)[:22]
        kb.append([InlineKeyboardButton(label, callback_data=f"rem:view:{rid}"), InlineKeyboardButton("✏️", callback_data=f"rem:edit:{rid}"), InlineKeyboardButton("🗑️", callback_data=f"rem:delete:{rid}")])
    kb.append([InlineKeyboardButton("➕ یادآوری جدید", callback_data="rem:add"), InlineKeyboardButton("🔄 بروزرسانی", callback_data="rem:list")])
    kb.append([InlineKeyboardButton("🔙 پروفایل", callback_data="rem:profile")])
    return InlineKeyboardMarkup(kb)

def _find(user_id,rid):
    for r in list_user_reminders(user_id,100):
        if int(r[0])==rid: return r
    return None

def detail_text(r):
    rid,text,when,rt,every,done,active=r
    return (f"⏰ یادآوری #{rid}\n━━━━━━━━━━━━━━━━\n📝 {text}\n🕐 {_fmt(when)}\n🔁 {_repeat(rt,every)}\n📌 وضعیت: {'فعال 🟢' if int(active or 0) and not int(done or 0) else 'غیرفعال ⏸️'}")

def detail_keyboard(r):
    rid,_,_,_,_,done,active=r
    toggle="⏸️ غیرفعال کن" if int(active or 0) else "▶️ فعال کن"
    return InlineKeyboardMarkup([[InlineKeyboardButton(toggle,callback_data=f"rem:toggle:{rid}"),InlineKeyboardButton("🕐 ویرایش زمان",callback_data=f"rem:time:{rid}")],[InlineKeyboardButton("📝 ویرایش متن",callback_data=f"rem:text:{rid}"),InlineKeyboardButton("🗑️ حذف",callback_data=f"rem:delete:{rid}")],[InlineKeyboardButton("🔙 لیست",callback_data="rem:list")]])

async def _h_reminder_manager(update, context, user_id):
    text,rows=reminder_manager_text(user_id)
    await update.message.reply_text(text, reply_markup=reminder_manager_keyboard(rows))

async def _h_reminder_input(update, context, user_id, text):
    waiting=context.user_data.get("reminder_edit")
    if not waiting: return False
    rid=int(waiting.get("rid"))
    mode=waiting.get("mode")
    row=_find(user_id,rid)
    if not row:
        context.user_data.pop("reminder_edit",None); await update.message.reply_text("❌ این یادآوری دیگر وجود ندارد."); return True
    if text in ("لغو","انصراف","cancel"):
        context.user_data.pop("reminder_edit",None); await _h_reminder_manager(update,context,user_id); return True
    if mode=="text":
        ok=update_reminder(user_id,rid,text=text.strip())
    else:
        parsed=parse_natural_reminder("یادآوری " + text)
        if not parsed:
            await update.message.reply_text("⚠️ زمان را واضح بنویس؛ مثلاً: «فردا ساعت ۹» یا «هر روز ساعت ۸»."); return True
        _,when,rt,every=parsed
        ok=update_reminder(user_id,rid,remind_at=when.isoformat(),repeat_type=rt,repeat_every=every)
    context.user_data.pop("reminder_edit",None)
    await update.message.reply_text("✅ یادآوری ویرایش شد." if ok else "❌ ویرایش انجام نشد.")
    await _h_reminder_manager(update,context,user_id)
    return True
