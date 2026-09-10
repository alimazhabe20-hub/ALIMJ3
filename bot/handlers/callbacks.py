from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import ContextTypes
from bot.database import get_user, get_user_city, set_last_main_msg_id
from bot.services.ai_service import (
    clear_history,
    available_providers,
    set_selected_provider,
    get_selected_model,
)
from bot.utils.helpers import (
    build_message,
    get_refresh_button,
    get_main_keyboard, get_more_keyboard, get_ai_keyboard, get_ai_model_keyboard,
    get_calendar_buttons,
    get_calendar_text,
)
from bot.api.calendar import get_today_tehran
from bot.handlers.middleware import check_and_rate_limit
from bot.config import config
from bot.logger import logger
import jdatetime
import asyncio
import html
import re
from datetime import datetime, timedelta


def datetime_now_date(tz_name: str, add_days: int = 0) -> str:
    """Return the user's calendar date in the selected timezone."""
    try:
        from bot.features.market.economic_calendar import _tz
        return (datetime.now(_tz(tz_name)) + timedelta(days=add_days)).strftime("%Y-%m-%d")
    except Exception:
        return (datetime.now() + timedelta(days=add_days)).strftime("%Y-%m-%d")


# جلوگیری از اجرای همزمان چند بروزرسانی برای یک کاربر
_refresh_locks = {}


def _get_refresh_lock(user_id: int):
    lock = _refresh_locks.get(user_id)
    if lock is None:
        # Keep the per-user lock map bounded during long-running bot sessions.
        # Stale unlocked entries are safe to discard; active locks are preserved.
        if len(_refresh_locks) > 2048:
            stale = [uid for uid, item in _refresh_locks.items() if not item.locked()]
            for uid in stale[:1024]:
                _refresh_locks.pop(uid, None)
        lock = asyncio.Lock()
        _refresh_locks[user_id] = lock
    return lock


async def _safe_answer(query, text: str = None, show_alert: bool = False):
    """پاسخ به callback فقط یک‌بار؛ اگر قبلاً جواب داده شده باشد بی‌صدا رد می‌شود."""
    try:
        if text is None:
            await query.answer()
        else:
            await query.answer(text, show_alert=show_alert)
    except Exception as _exc:
        logger.debug("%s: %s", __name__, _exc)


def _set_ec_view(context, *, mode="today", impact="all", currency="", date_str=""):
    context.user_data["ec_view"] = {
        "mode": mode, "impact": impact, "currency": currency, "date_str": date_str,
    }


def _ec_view(context):
    view = context.user_data.get("ec_view") or {}
    return {
        "mode": view.get("mode", "today"),
        "impact": view.get("impact", "all"),
        "currency": view.get("currency", ""),
        "date_str": view.get("date_str", ""),
    }


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    # نکته مهم: callback_query را فقط یک‌بار می‌توان answer کرد.
    # answer اولیه را حذف کردیم تا شاخه‌هایی که نیاز به Toast دارند
    # (مثل refresh_main و عضویت کانال) بتوانند پیام مناسب نشان دهند.

    if not await check_and_rate_limit(update, context):
        # middleware در صورت نیاز خودش answer کرده؛ در غیر این صورت spinner را قطع می‌کنیم
        await _safe_answer(query)
        return

    data = query.data
    user_id = update.effective_user.id

    # ───────────────── تقویم اقتصادی بازار ─────────────────
    if data and data.startswith("ec:"):
        from bot.features.market.economic_calendar import (
            get_calendar_for_user, calendar_text, get_calendar_keyboard,
            get_settings_keyboard, get_lead_keyboard, get_tz_keyboard,
            get_event_keyboard, get_event, refresh_calendar, event_detail,
            ai_context,
        )
        from bot.database import get_economic_calendar_preferences, set_economic_calendar_preferences
        try:
            if data == "ec:today":
                _set_ec_view(context, mode="today", impact="all")
                events, tz_name = await get_calendar_for_user(user_id, "today", "all")
                await _safe_answer(query)
                await query.edit_message_text(calendar_text(events, title="تقویم اقتصادی امروز", tz_name=tz_name), parse_mode="HTML", reply_markup=get_calendar_keyboard(user_id, mode="today", impact="all", events=events, selected_date=datetime_now_date(tz_name)))
                return
            if data == "ec:tomorrow":
                _set_ec_view(context, mode="tomorrow", impact="all")
                events, tz_name = await get_calendar_for_user(user_id, "tomorrow", "all")
                await _safe_answer(query)
                await query.edit_message_text(calendar_text(events, title="تقویم اقتصادی فردا", tz_name=tz_name), parse_mode="HTML", reply_markup=get_calendar_keyboard(user_id, mode="tomorrow", impact="all", events=events, selected_date=datetime_now_date(tz_name, 1)))
                return
            if data == "ec:week":
                _set_ec_view(context, mode="week", impact="all")
                events, tz_name = await get_calendar_for_user(user_id, "week", "all")
                await _safe_answer(query)
                await query.edit_message_text(calendar_text(events, title="تقویم اقتصادی هفته", tz_name=tz_name), parse_mode="HTML", reply_markup=get_calendar_keyboard(user_id, mode="week", impact="all", events=events, selected_date=datetime_now_date(tz_name)))
                return
            if data == "ec:impact:high":
                _set_ec_view(context, mode="today", impact="high")
                events, tz_name = await get_calendar_for_user(user_id, "today", "high")
                await _safe_answer(query, "فقط خبرهای مهم")
                await query.edit_message_text(calendar_text(events, title="خبرهای مهم اقتصادی امروز", tz_name=tz_name), parse_mode="HTML", reply_markup=get_calendar_keyboard(user_id, mode="today", impact="high", events=events, selected_date=datetime_now_date(tz_name)))
                return
            if data == "ec:impact:all":
                _set_ec_view(context, mode="today", impact="all")
                events, tz_name = await get_calendar_for_user(user_id, "today", "all")
                await _safe_answer(query)
                await query.edit_message_text(calendar_text(events, title="تقویم اقتصادی امروز", tz_name=tz_name), parse_mode="HTML", reply_markup=get_calendar_keyboard(user_id, mode="today", impact="all", events=events, selected_date=datetime_now_date(tz_name)))
                return
            if data.startswith("ec:cur:"):
                cur = data.split(":", 2)[2].upper()
                _set_ec_view(context, mode="today", impact="all", currency=cur)
                events, tz_name = await get_calendar_for_user(user_id, "today", "all", cur)
                await _safe_answer(query, f"فیلتر {cur}")
                await query.edit_message_text(calendar_text(events, title=f"خبرهای {cur} امروز", tz_name=tz_name), parse_mode="HTML", reply_markup=get_calendar_keyboard(user_id, mode="today", impact="all", currency=cur, events=events, selected_date=datetime_now_date(tz_name)))
                return
            if data == "ec:noop":
                await _safe_answer(query)
                return
            if data == "ec:refresh":
                await _safe_answer(query, "در حال بروزرسانی…")
                await refresh_calendar(force=True)
                events, tz_name = await get_calendar_for_user(user_id, "today", "all")
                await query.edit_message_text(
                    calendar_text(events, title="تقویم اقتصادی امروز", tz_name=tz_name),
                    parse_mode="HTML",
                    reply_markup=get_calendar_keyboard(user_id, mode="today", impact="all", events=events, selected_date=datetime_now_date(tz_name)),
                )
                return
            if data.startswith("ec:date:"):
                selected_date = data.split(":", 2)[2]
                events, tz_name = await get_calendar_for_user(user_id, "today", "all", date_str=selected_date)
                await _safe_answer(query)
                await query.edit_message_text(
                    calendar_text(events, title=f"تقویم اقتصادی {selected_date}", tz_name=tz_name),
                    parse_mode="HTML",
                    reply_markup=get_calendar_keyboard(user_id, mode="today", impact="all", events=events, selected_date=selected_date),
                )
                return
            if data.startswith("ec:page:"):
                parts = data.split(":", 6)
                if len(parts) != 7:
                    await _safe_answer(query, "صفحه نامعتبر است.", show_alert=True)
                    return
                _, _, page_s, mode, selected_date, impact, currency = parts
                page = max(0, int(page_s))
                events, tz_name = await get_calendar_for_user(
                    user_id, mode or "today", impact or "all", currency or "", selected_date or ""
                )
                if mode == "week":
                    title = "تقویم اقتصادی هفته"
                elif mode == "tomorrow":
                    title = "تقویم اقتصادی فردا"
                elif impact == "high":
                    title = "خبرهای مهم اقتصادی امروز"
                elif currency:
                    title = f"خبرهای {currency} امروز"
                else:
                    title = "تقویم اقتصادی امروز"
                await _safe_answer(query)
                await query.edit_message_text(
                    calendar_text(events, title=title, tz_name=tz_name),
                    parse_mode="HTML",
                    reply_markup=get_calendar_keyboard(
                        user_id, mode=mode or "today", impact=impact or "all", currency=currency or "",
                        events=events, selected_date=selected_date, page=page
                    ),
                )
                return
            if data == "ec:noop":
                await _safe_answer(query)
                return

            if data.startswith("ec:page:"):
                page = max(0, int(data.split(":", 2)[2]))
                view = _ec_view(context)
                events, tz_name = await get_calendar_for_user(
                    user_id, view["mode"], view["impact"], view["currency"], view["date_str"]
                )
                await _safe_answer(query)
                await query.edit_message_reply_markup(
                    reply_markup=get_calendar_keyboard(user_id, events=events, selected_date=view["date_str"], page=page)
                )
                return

            if data.startswith("ec:date:"):
                date_str = data.split(":", 2)[2]
                _set_ec_view(context, mode="date", impact="all", date_str=date_str)
                events, tz_name = await get_calendar_for_user(user_id, "today", "all", date_str=date_str)
                await _safe_answer(query)
                await query.edit_message_text(
                    calendar_text(events, title=f"تقویم اقتصادی {date_str}", tz_name=tz_name),
                    parse_mode="HTML",
                    reply_markup=get_calendar_keyboard(user_id, events=events, selected_date=date_str),
                )
                return

            if data == "ec:refresh":
                view = _ec_view(context)
                await _safe_answer(query, "در حال بروزرسانی…")
                await refresh_calendar(force=True)
                events, tz_name = await get_calendar_for_user(
                    user_id, view["mode"], view["impact"], view["currency"], view["date_str"]
                )
                await query.edit_message_text(
                    calendar_text(events, title="تقویم اقتصادی امروز" if view["mode"] == "today" else "تقویم اقتصادی", tz_name=tz_name),
                    parse_mode="HTML",
                    reply_markup=get_calendar_keyboard(user_id, events=events, selected_date=view["date_str"]),
                )
                return

            if data == "ec:noop":
                await _safe_answer(query)
                return

            if data.startswith("ec:page:"):
                # ec:page:<page>:<mode>:<date>:<impact>:<currency>
                parts = data.split(":", 6)
                if len(parts) < 6:
                    await _safe_answer(query, "صفحه نامعتبر است.", show_alert=True)
                    return
                try:
                    page = max(0, int(parts[2]))
                except Exception:
                    page = 0
                mode = parts[3] or "today"
                selected_date = parts[4] or ""
                impact = parts[5] or "all"
                currency = parts[6].upper() if len(parts) > 6 and parts[6] else ""
                events, tz_name = await get_calendar_for_user(
                    user_id, mode, impact, currency, selected_date
                )
                await _safe_answer(query)
                await query.edit_message_reply_markup(
                    reply_markup=get_calendar_keyboard(
                        user_id, mode=mode, impact=impact, currency=currency,
                        events=events, selected_date=selected_date, page=page
                    )
                )
                return

            if data.startswith("ec:date:"):
                selected_date = data.split(":", 2)[2]
                events, tz_name = await get_calendar_for_user(
                    user_id, "today", "all", "", selected_date
                )
                await _safe_answer(query)
                await query.edit_message_text(
                    calendar_text(events, title=f"تقویم اقتصادی {selected_date}", tz_name=tz_name),
                    parse_mode="HTML",
                    reply_markup=get_calendar_keyboard(
                        user_id, mode="today", impact="all", events=events,
                        selected_date=selected_date, page=0
                    ),
                )
                return

            if data == "ec:refresh":
                await _safe_answer(query, "در حال بروزرسانی…")
                await refresh_calendar(force=True)
                events, tz_name = await get_calendar_for_user(user_id, "today", "all")
                await query.edit_message_text(
                    calendar_text(events, title="تقویم اقتصادی امروز", tz_name=tz_name),
                    parse_mode="HTML",
                    reply_markup=get_calendar_keyboard(user_id, events=events, page=0),
                )
                return

            if data == "ec:settings":
                await _safe_answer(query)
                await query.edit_message_reply_markup(reply_markup=get_settings_keyboard(user_id))
                return
            if data == "ec:toggle_alert":
                p = get_economic_calendar_preferences(user_id)
                set_economic_calendar_preferences(user_id, alerts=not p["alerts"])
                await _safe_answer(query, "اعلان‌ها روشن شد ✅" if not p["alerts"] else "اعلان‌ها خاموش شد 🔕")
                await query.edit_message_reply_markup(reply_markup=get_settings_keyboard(user_id))
                return
            if data == "ec:lead_menu":
                await _safe_answer(query)
                await query.edit_message_reply_markup(reply_markup=get_lead_keyboard())
                return
            if data.startswith("ec:lead:"):
                minutes = int(data.split(":", 2)[2])
                set_economic_calendar_preferences(user_id, lead_minutes=minutes)
                await _safe_answer(query, f"هشدار {minutes} دقیقه قبل تنظیم شد")
                await query.edit_message_reply_markup(reply_markup=get_settings_keyboard(user_id))
                return
            if data == "ec:tz_menu":
                await _safe_answer(query)
                await query.edit_message_reply_markup(reply_markup=get_tz_keyboard())
                return
            if data.startswith("ec:tz:"):
                tz_name = data.split(":", 2)[2]
                set_economic_calendar_preferences(user_id, timezone=tz_name)
                await _safe_answer(query, "منطقه زمانی ذخیره شد ✅")
                await query.edit_message_reply_markup(reply_markup=get_settings_keyboard(user_id))
                return
            if data == "ec:impact_menu":
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                await _safe_answer(query)
                await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔴 فقط زیاد", callback_data="ec:setimpact:high"), InlineKeyboardButton("🟠 زیاد + متوسط", callback_data="ec:setimpact:medium")],
                    [InlineKeyboardButton("📋 همه", callback_data="ec:setimpact:all")],
                    [InlineKeyboardButton("↩️ برگشت", callback_data="ec:settings")],
                ]))
                return
            if data.startswith("ec:setimpact:"):
                impact = data.split(":", 2)[2]
                set_economic_calendar_preferences(user_id, impact=impact)
                await _safe_answer(query, "فیلتر اهمیت ذخیره شد ✅")
                await query.edit_message_reply_markup(reply_markup=get_settings_keyboard(user_id))
                return
            if data == "ec:ai":
                _set_ec_view(context, mode="today", impact="all")
                await _safe_answer(query, "در حال تحلیل هوشمند…")
                events, tz_name = await get_calendar_for_user(user_id, "today", "all")
                context_text = ai_context(events, tz_name, 60)
                from bot.services.ai_service import ask_ai
                prompt = (
                    "تو یک تحلیل‌گر حرفه‌ای اقتصاد کلان و بازارهای مالی هستی. پاسخ را کاملاً فارسی، منظم و کاربردی بده. "
                    "فقط از داده‌های تقویم استفاده کن و هیچ عدد، خبر یا نتیجه قطعی اختراع نکن. برای هر رویداد مهم، ابتدا "
                    "معنای خبر و تفاوت Actual با Forecast و Previous را توضیح بده. سپس اثر احتمالی آن را جداگانه روی "
                    "1) بیت‌کوین و اتریوم، 2) آلت‌کوین‌ها، 3) دلار آمریکا و DXY، 4) طلا، 5) سهام، 6) اوراق و بازدهی خزانه‌داری "
                    "بررسی کن. اگر Actual بالاتر از Forecast، پایین‌تر از Forecast، نزدیک Forecast یا هنوز منتشر نشده است، "
                    "سناریوهای مربوط به هر حالت را توضیح بده و جهت احتمالی بازار را با عبارت‌هایی مثل «معمولاً»، «می‌تواند» "
                    "و «در صورت تداوم» بیان کن؛ هرگز آن را تضمین یا سیگنال قطعی معامله معرفی نکن. Previous را هم برای تشخیص "
                    "بهبود/بدترشدن روند در نظر بگیر. در پایان، «سناریوی پایه»، «سناریوی صعودی برای ریسک‌پذیری»، "
                    "«سناریوی نزولی برای ریسک‌پذیری» و «مهم‌ترین ریسک/ابهام» را کوتاه جمع‌بندی کن. اگر داده‌ای برای مقایسه وجود ندارد، "
                    "صریحاً بگو «داده کافی برای مقایسه وجود ندارد». پاسخ را بدون Markdown و بدون جدول بده. "
                    "پاسخ باید کامل باشد و هیچ جمله یا تیتر ناتمام نماند.\n\n"
                    "داده تقویم:\n" + context_text[:6500]
                )
                answer, _ = await ask_ai(user_id, prompt)
                from html import escape

                def _split_ai_text(txt: str, limit: int = 3600):
                    txt = (txt or "").strip()
                    if not txt:
                        return ["تحلیل در دسترس نیست."]
                    parts, buf, size = [], [], 0
                    for line in txt.splitlines() or [txt]:
                        piece = line.strip()
                        add = len(piece) + (1 if buf else 0)
                        if buf and size + add > limit:
                            parts.append("\n".join(buf).strip())
                            buf, size = [], 0
                        if len(piece) > limit:
                            if buf:
                                parts.append("\n".join(buf).strip())
                                buf, size = [], 0
                            while len(piece) > limit:
                                parts.append(piece[:limit])
                                piece = piece[limit:]
                            if piece:
                                buf, size = [piece], len(piece)
                        elif piece:
                            buf.append(piece)
                            size += add
                    if buf:
                        parts.append("\n".join(buf).strip())
                    return parts or ["تحلیل در دسترس نیست."]

                chunks = _split_ai_text(answer, 3600)
                first = escape(chunks[0], quote=False)
                text = (
                    "🤖 <b>تحلیل هوشمند تقویم اقتصادی</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "<i>اثر احتمالی بر کریپتو، دلار، طلا، سهام و اوراق</i>\n\n"
                    f"<blockquote>{first}</blockquote>"
                )
                await query.message.reply_text(
                    text,
                    parse_mode="HTML",
                    reply_markup=get_calendar_keyboard(user_id, mode="today", impact="all", events=events),
                )
                for idx, chunk in enumerate(chunks[1:], start=2):
                    continuation = (
                        f"🤖 <b>ادامه تحلیل هوشمند ({idx}/{len(chunks)})</b>\n"
                        "━━━━━━━━━━━━━━━━━━━━\n"
                        f"<blockquote>{escape(chunk, quote=False)}</blockquote>"
                    )
                    await query.message.reply_text(continuation, parse_mode="HTML")
                return
            if data.startswith("ec:event:"):
                event_id = data.split(":", 2)[2]
                events = await refresh_calendar()
                p = get_economic_calendar_preferences(user_id)
                tz_name = p["timezone"] or getattr(config, "TIMEZONE", "Asia/Tehran")
                e = get_event(events, event_id)
                if not e:
                    await _safe_answer(query, "این خبر دیگر در فهرست فعلی نیست.", show_alert=True)
                    return
                await _safe_answer(query)
                await query.edit_message_text(event_detail(e, tz_name), parse_mode="HTML", reply_markup=get_event_keyboard(event_id))
                return
            if data.startswith("ec:analyze:"):
                event_id = data.split(":", 2)[2]
                await _safe_answer(query, "در حال تحلیل…")
                events = await refresh_calendar()
                p = get_economic_calendar_preferences(user_id)
                tz_name = p["timezone"] or getattr(config, "TIMEZONE", "Asia/Tehran")
                e = get_event(events, event_id)
                if not e:
                    await _safe_answer(query, "این خبر دیگر در فهرست فعلی نیست.", show_alert=True)
                    return
                from bot.services.ai_service import ask_ai
                prompt = (
                    "تو تحلیل‌گر ارشد اقتصاد کلان و بازارهای مالی هستی. این رویداد را عمیق، کاربردی و کاملاً فارسی تحلیل کن. "
                    "داده‌های عددی رویداد منبع حقیقت هستند؛ هیچ عدد، خبر، سخنرانی، تصمیم بانک مرکزی یا رویداد دیگری که در ورودی نیست اضافه نکن. "
                    "اما برای تفسیر اثر بازار، از روابط استاندارد اقتصاد کلان استفاده کن؛ مثلاً داده تورمی قوی‌تر یا ضعیف‌تر از انتظار "
                    "را از مسیر تورم، سیاست پولی، نرخ بهره، بازدهی اوراق و قدرت دلار به دارایی‌ها وصل کن. این روابط را به‌عنوان «اثر معمول/احتمالی» بیان کن، نه واقعیت قطعی. "
                    "اول دقیقاً مشخص کن Actual نسبت به Forecast و Previous چه پیامی دارد و آیا سورپرایز مثبت، منفی یا خنثی است. "
                    "اگر واحد یا جهت شاخص مهم است، توضیح بده که بالا/پایین رفتن همین شاخص معمولاً چه معنایی دارد؛ صرفاً از قانون ساده «عدد بالاتر = خوب» استفاده نکن. "
                    "سپس زنجیره انتقال اثر را توضیح بده: داده → انتظار سیاست پولی → نرخ‌ها/بازدهی → DXY → نقدینگی و ریسک‌پذیری → دارایی‌ها. "
                    "برای کریپتو، بیت‌کوین و اتریوم را جدا از آلت‌کوین‌ها در نظر بگیر و تفاوت واکنش احتمالی را توضیح بده. "
                    "برای هر بخش اگر اثر مستقیم یا قابل اتکایی از این داده وجود ندارد، صریحاً بگو اثر مستقیم محدود است و از نتیجه‌گیری ساختگی خودداری کن. "
                    "بین «آنچه داده واقعاً نشان می‌دهد» و «سناریوی بازار» تفاوت روشن بگذار. توصیه قطعی خرید/فروش، تارگت قیمتی یا پیش‌بینی عددی نساز. "
                    "پاسخ را بدون Markdown و بدون جدول بنویس و حتماً با تیترهای کوتاه دقیقاً در همین ترتیب جدا کن: "
                    "«معنی خبر»، «کریپتو»، «دلار/DXY»، «طلا»، «سهام»، «اوراق و بازدهی»، «سناریوی Actual در برابر Forecast»، «جمع‌بندی». "
                    "در «جمع‌بندی» یک جهت‌گیری احتمالی کلی برای ریسک‌پذیری بازار بده (مثلاً ریسک‌پذیرتر، ریسک‌گریزتر یا خنثی) و دلیلش را کوتاه بگو. "
                    "اگر Actual منتشر نشده است، تحلیل را بر اساس سناریوهای بالاتر/پایین‌تر/مطابق انتظار انجام بده و آن را به‌عنوان نتیجه واقعی معرفی نکن. "
                    "پاسخ باید کامل و خودبسنده باشد و هیچ جمله یا تیتر ناتمام نماند. برای هر تیتر 2 تا 4 جمله کافی است؛ کل پاسخ را حدود 2200 تا 3200 کاراکتر نگه دار.\n\n"
                    "داده رویداد هدف:\n" + ai_context([e], tz_name) +
                    "\n\nکانتکست تقویم اقتصادی مرتبط:\n" + ai_context(events, tz_name, limit=60)
                )
                answer, _ = await ask_ai(user_id, prompt)
                from html import escape

                # Telegram text messages support up to 4096 chars. Never truncate an
                # AI answer mid-sentence: split it at paragraph/line boundaries and
                # keep the event message + first analysis part on the original message.
                def _split_ai_text(txt: str, limit: int = 3800):
                    txt = (txt or "").strip()
                    if not txt:
                        return ["تحلیل در دسترس نیست."]
                    parts, buf, size = [], [], 0
                    for line in txt.splitlines():
                        piece = line.strip()
                        add = len(piece) + (1 if buf else 0)
                        if buf and size + add > limit:
                            parts.append("\n".join(buf).strip())
                            buf, size = [], 0
                        if len(piece) > limit:
                            if buf:
                                parts.append("\n".join(buf).strip())
                                buf, size = [], 0
                            while len(piece) > limit:
                                parts.append(piece[:limit])
                                piece = piece[limit:]
                            if piece:
                                buf, size = [piece], len(piece)
                        elif piece:
                            buf.append(piece)
                            size += add
                    if buf:
                        parts.append("\n".join(buf).strip())
                    return parts or ["تحلیل در دسترس نیست."]

                chunks = _split_ai_text(answer, 3600)
                first = escape(chunks[0], quote=False)
                text = event_detail(e, tz_name) + (
                    "\n\n🤖 <b>تحلیل هوشمند بازار</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    f"<blockquote>{first}</blockquote>"
                )
                # بخش اول روی همان پیام رویداد قرار می‌گیرد. ادامه تحلیل بدون حذف
                # یا کوتاه‌کردن، در پیام‌های بعدی ارسال می‌شود.
                await query.edit_message_text(text, parse_mode="HTML", reply_markup=get_event_keyboard(event_id))
                for idx, chunk in enumerate(chunks[1:], start=2):
                    continuation = (
                        f"🤖 <b>ادامه تحلیل هوشمند بازار ({idx}/{len(chunks)})</b>\n"
                        "━━━━━━━━━━━━━━━━━━━━\n"
                        f"<blockquote>{escape(chunk, quote=False)}</blockquote>"
                    )
                    await query.message.reply_text(continuation, parse_mode="HTML")
                return
            if data == "ec:back":
                _set_ec_view(context, mode="today", impact="all")
                events, tz_name = await get_calendar_for_user(user_id, "today", "all")
                await _safe_answer(query)
                await query.edit_message_text(calendar_text(events, title="تقویم اقتصادی امروز", tz_name=tz_name), parse_mode="HTML", reply_markup=get_calendar_keyboard(user_id, mode="today", impact="all", events=events, selected_date=datetime_now_date(tz_name)))
                return
        except Exception as e:
            logger.error("economic calendar callback failed: %s", e, exc_info=True)
            await _safe_answer(query, "⚠️ خطا در تقویم اقتصادی.", show_alert=True)
            return

    if data == "ai_models":
        await _safe_answer(query)
        await query.edit_message_reply_markup(reply_markup=get_ai_model_keyboard(user_id))
        return

    if data == "ai_models_back":
        await _safe_answer(query)
        await query.edit_message_reply_markup(reply_markup=get_ai_keyboard(user_id))
        return

    if data == "ai_noop":
        await _safe_answer(query, "هیچ مدل فعالی تنظیم نشده است.", show_alert=True)
        return

    if data.startswith("ai_provider:") or data.startswith("ai_model:"):
        # ai_provider: انتخاب ارائه‌دهنده (همه مدل‌هایش شامل می‌شود)
        # ai_model: سازگاری با پیام‌های قدیمی
        try:
            index = int(data.split(":", 1)[1])
            providers = available_providers()
            provider, label = providers[index]
        except (ValueError, IndexError):
            await _safe_answer(query, "❌ این سرویس دیگر در دسترس نیست.", show_alert=True)
            return
        set_selected_provider(user_id, provider)
        await _safe_answer(query, f"✅ فعال شد: {label}", show_alert=False)
        await query.edit_message_reply_markup(reply_markup=get_ai_keyboard(user_id))
        return

    if data == "ai_clear_memory":
        clear_history(user_id)
        await _safe_answer(query, "حافظه AI پاک شد ✅", show_alert=False)
        try:
            await query.edit_message_reply_markup(
                reply_markup=get_ai_keyboard(user_id)
            )
        except Exception as _exc:
            logger.debug("%s: %s", __name__, _exc)
        await query.message.reply_text("✅ حافظه گفت‌وگو و خلاصه پاک شد. (حافظه بلندمدت با «پاک کردن همه حافظه» حذف می‌شود)")
        return

    if data == "ai_exit":
        context.user_data.pop("ai_mode", None)
        context.user_data.pop("ai_shopping_mode", None)
        context.user_data.pop("waiting_for", None)
        await _safe_answer(query)
        await query.message.reply_text("➕ منوی بیشتر:", reply_markup=get_more_keyboard())
        return

    if data.startswith("ai_tts:"):
        from bot.services.ai_extras import get_stored_answer
        from bot.services.ai_service import text_to_speech
        from io import BytesIO
        aid = data.split(":", 1)[1]
        text = get_stored_answer(aid, user_id)
        if not text:
            await _safe_answer(query, "این جواب منقضی شده. دوباره بپرس.", show_alert=True)
            return
        await _safe_answer(query, "در حال ویس دادن...")
        try:
            notice = await query.message.reply_text("🔊 در حال ویس دادن...")
            audio = await text_to_speech(text)
            bio = BytesIO(audio)
            bio.name = "answer.mp3"
            await query.message.reply_audio(audio=bio, caption="🔊")
            try:
                await notice.delete()
            except Exception as _exc:
                logger.debug("%s: %s", __name__, _exc)
        except Exception as e:
            await query.message.reply_text(f"⚠️ ویس ساخته نشد: {e}")
        return

    if data.startswith("ai_quick:"):
        kind = data.split(":", 1)[1]
        await _safe_answer(query)
        try:
            city = get_user_city(user_id) or "تهران"
            if kind == "weather":
                from bot.api.weather import get_weather, format_weather
                w = get_weather(city)
                txt = format_weather(city, w)
            elif kind == "price":
                from bot.features.market.finance import full_market_prices
                txt = await full_market_prices()
            elif kind == "istikhara":
                from bot.features.religious.istikhara import istikhara
                txt = await istikhara(user_id)
            elif kind == "prayer":
                from bot.api.prayer import get_prayer_times
                pt = get_prayer_times(city)
                if pt:
                    txt = f"🕌 اوقات شرعی {city}:\n" + "\n".join(f"{k}: {v}" for k, v in pt.items())
                else:
                    txt = "اوقات شرعی در دسترس نیست."
            else:
                txt = "دکمه نامعتبر."
            await query.message.reply_text(txt)
        except Exception as e:
            await query.message.reply_text(f"⚠️ {e}")
        return

    # ───────────────── بروزرسانی منوی اصلی ─────────────────
    if data == "refresh_main":
        from bot.logger import logger

        lock = _get_refresh_lock(user_id)

        if lock.locked():
            await _safe_answer(query, "⏳ بروزرسانی قبلی هنوز در حال انجام است.", show_alert=False)
            return

        async with lock:
            await _safe_answer(query, "🔄 در حال بروزرسانی...", show_alert=False)

            chat_id = None
            message_id = None
            try:
                if query.message is not None:
                    chat_id = query.message.chat_id
                    message_id = query.message.message_id
                elif update.effective_chat is not None:
                    chat_id = update.effective_chat.id
            except Exception as e:
                logger.warning("refresh_main resolve chat: %s", e)
                try:
                    chat_id = update.effective_chat.id if update.effective_chat else None
                except Exception:
                    chat_id = None

            try:
                user_row = None
                try:
                    user_row = get_user(user_id)
                except Exception as e:
                    logger.warning("refresh_main get_user: %s", e)

                first_name = "کاربر"
                try:
                    if user_row and len(user_row) > 1 and user_row[1]:
                        first_name = str(user_row[1])
                except Exception as _exc:
                    logger.debug("%s: %s", __name__, _exc)

                city = "قم"
                try:
                    city = get_user_city(user_id) or "قم"
                except Exception as e:
                    logger.warning("refresh_main get_user_city: %s", e)

                try:
                    message = await build_message(user_id, first_name, city)
                except Exception as e:
                    logger.error("refresh_main build_message: %s", e, exc_info=True)
                    message = (
                        f"🌟 سلام {first_name} عزیز!\n\n"
                        f"⚠️ بارگذاری اطلاعات با خطا مواجه شد.\n"
                        f"کد: {type(e).__name__}\n"
                        f"/start را بفرستید."
                    )

                if not message:
                    message = "⚠️ محتوا خالی بود. /start را بفرستید."
                if len(message) > 4000:
                    message = message[:3990] + "\n…"

                sent = False

                # روش ۱: edit از طریق callback_query
                if not sent:
                    try:
                        await query.edit_message_text(
                            text=message,
                            reply_markup=get_refresh_button(),
                        )
                        sent = True
                        if message_id:
                            context.user_data["last_main_msg_id"] = message_id
                            try:
                                set_last_main_msg_id(user_id, message_id)
                            except Exception as _exc:
                                logger.debug("%s: %s", __name__, _exc)
                    except BadRequest as e:
                        err = str(e).lower()
                        if "message is not modified" in err or "not modified" in err:
                            sent = True
                        else:
                            logger.warning("refresh_main query.edit BadRequest: %s", e)
                    except Exception as e:
                        logger.warning("refresh_main query.edit: %s", e)

                # روش ۲: edit مستقیم با bot API
                if not sent and chat_id and message_id:
                    try:
                        await context.bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=message_id,
                            text=message,
                            reply_markup=get_refresh_button(),
                        )
                        sent = True
                        context.user_data["last_main_msg_id"] = message_id
                        try:
                            set_last_main_msg_id(user_id, message_id)
                        except Exception as _exc:
                            logger.debug("%s: %s", __name__, _exc)
                    except BadRequest as e:
                        err = str(e).lower()
                        if "message is not modified" in err or "not modified" in err:
                            sent = True
                        else:
                            logger.warning("refresh_main bot.edit BadRequest: %s", e)
                    except Exception as e:
                        logger.warning("refresh_main bot.edit: %s", e)

                # روش ۳: ارسال پیام جدید
                if not sent and chat_id:
                    try:
                        msg = await context.bot.send_message(
                            chat_id=chat_id,
                            text=message,
                            reply_markup=get_refresh_button(),
                        )
                        sent = True
                        context.user_data["last_main_msg_id"] = msg.message_id
                        try:
                            set_last_main_msg_id(user_id, msg.message_id)
                        except Exception as _exc:
                            logger.debug("%s: %s", __name__, _exc)
                        if message_id:
                            try:
                                await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
                            except Exception as _exc:
                                logger.debug("%s: %s", __name__, _exc)
                    except Exception as e:
                        logger.error("refresh_main send: %s", e, exc_info=True)

                if not sent:
                    tip = "⚠️ بروزرسانی انجام نشد."
                    if chat_id:
                        tip += " لطفاً /start را بفرستید."
                    else:
                        tip += " چت پیدا نشد؛ /start را بفرستید."
                    try:
                        if chat_id:
                            await context.bot.send_message(chat_id=chat_id, text=tip)
                    except Exception as _exc:
                        logger.debug("%s: %s", __name__, _exc)

            except Exception as e:
                logger.error("refresh_main outer: %s", e, exc_info=True)
                try:
                    cid = chat_id
                    if cid is None and update.effective_chat:
                        cid = update.effective_chat.id
                    if cid:
                        await context.bot.send_message(
                            chat_id=cid,
                            text=(
                                "⚠️ بروزرسانی موقتاً ناموفق بود.\n"
                                f"کد خطا: {type(e).__name__}: {str(e)[:120]}\n"
                                "چند ثانیه بعد دوباره بزنید یا /start بفرستید."
                            ),
                        )
                except Exception as _exc:
                    logger.debug("%s: %s", __name__, _exc)
        return

    if data == "back_to_main":
        await _safe_answer(query)
        try:
            user_row = get_user(user_id)
            first_name = (
                (user_row[1] if user_row and len(user_row) > 1 and user_row[1] else None)
                or "کاربر"
            )
            try:
                city = get_user_city(user_id) or "قم"
            except Exception:
                city = "قم"

            try:
                message = await build_message(user_id, first_name, city)
            except Exception as e:
                logger.error(
                    f"build_message failed in back_to_main: {type(e).__name__}: {e}",
                    exc_info=True,
                )
                message = (
                    f"🌟 سلام {first_name} عزیز!\n\n"
                    f"⚠️ بارگذاری کامل اطلاعات با خطا مواجه شد.\n"
                    f"دستور /start را بفرستید.\n"
                    f"({type(e).__name__})"
                )

            if len(message) > 4000:
                message = message[:3990] + "\n…"

            sent = False
            # 1) ویرایش همان پیام
            try:
                await query.edit_message_text(message, reply_markup=get_refresh_button())
                context.user_data["last_main_msg_id"] = query.message.message_id
                try:
                    set_last_main_msg_id(user_id, query.message.message_id)
                except Exception as _exc:
                    logger.debug("%s: %s", __name__, _exc)
                sent = True
            except Exception as e1:
                logger.warning(f"back_to_main edit failed: {type(e1).__name__}: {e1}")

            # 2) اگر edit نشد، پیام جدید با bot.send_message
            if not sent:
                try:
                    msg = await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=message,
                        reply_markup=get_refresh_button(),
                    )
                    context.user_data["last_main_msg_id"] = msg.message_id
                    try:
                        set_last_main_msg_id(user_id, msg.message_id)
                    except Exception as _exc:
                        logger.debug("%s: %s", __name__, _exc)
                    sent = True
                    try:
                        await query.message.delete()
                    except Exception as _exc:
                        logger.debug("%s: %s", __name__, _exc)
                except Exception as e2:
                    logger.error(
                        f"back_to_main send failed: {type(e2).__name__}: {e2}",
                        exc_info=True,
                    )

            # کیبورد اصلی پایین
            try:
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="",
                    reply_markup=get_main_keyboard(user_id),
                )
            except Exception as _exc:
                logger.debug("%s: %s", __name__, _exc)

            if not sent:
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="⚠️ بازگشت به منو ناموفق بود. لطفاً /start را بفرستید.",
                )
        except Exception as e:
            logger.error(f"back_to_main outer error: {type(e).__name__}: {e}", exc_info=True)
            try:
                chat_id = update.effective_chat.id if update.effective_chat else None
                if chat_id:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=(
                            "⚠️ موقتاً مشکلی پیش آمد. دستور /start را بفرستید.\n"
                            f"کد خطا: {type(e).__name__}"
                        ),
                    )
            except Exception as _exc:
                logger.debug("%s: %s", __name__, _exc)
        return

    if data == "calendar_today":
        await _safe_answer(query)
        today = get_today_tehran()
        text = get_calendar_text(today.year, today.month, today.day, user_id)
        await query.edit_message_text(
            text,
            reply_markup=get_calendar_buttons(today.year, today.month, today.day, user_id)
        )
        return

    if data.startswith("day_"):
        await _safe_answer(query)
        parts = data.split("_")
        year, month, day = int(parts[1]), int(parts[2]), int(parts[3])
        try:
            jdatetime.date(year, month, day)
        except ValueError:
            if day < 1:
                month -= 1
                if month < 1:
                    month = 12
                    year -= 1
                last_day = jdatetime.date(year, month, 1) - jdatetime.timedelta(days=1)
                day = last_day.day
            else:
                month += 1
                if month > 12:
                    month = 1
                    year += 1
                day = 1
        text = get_calendar_text(year, month, day, user_id)
        await query.edit_message_text(
            text,
            reply_markup=get_calendar_buttons(year, month, day, user_id)
        )
        return

    if data.startswith("cal_"):
        await _safe_answer(query)
        parts = data.split("_")
        year, month, day = int(parts[1]), int(parts[2]), int(parts[3])
        if month < 1:
            month = 12
            year -= 1
        elif month > 12:
            month = 1
            year += 1
        text = get_calendar_text(year, month, day, user_id)
        await query.edit_message_text(
            text,
            reply_markup=get_calendar_buttons(year, month, day, user_id)
        )
        return


    # ── منوی تحلیل کریپتو (cx:action:symbol) — ویرایش همان پیام ──
    if data.startswith("cx:"):
        await _safe_answer(query)
        parts = data.split(":")
        if len(parts) < 3:
            return
        action, symbol = parts[1], parts[2]
        context.user_data["crypto_symbol"] = symbol
        try:
            from bot.features.market.finance import (
                analyze_crypto, analyze_gold, get_crypto_chart, get_gold_chart, get_crypto_analysis_keyboard,
                trading_recommendation, derivatives_radar, risk_scenarios,
                position_size_guide, entry_alert_text, market_scanner,
            )
            from io import BytesIO
            from telegram import InputMediaPhoto

            is_gold = symbol.lower() in ("gold", "xau", "xauusd", "xau/usd")
            # این منو باید Inline باشد تا همان پیام نمودار بتواند با تغییر تایم‌فریم ویرایش شود.
            # ReplyKeyboard در اینجا باعث می‌شد پیام تحلیل از جریان «بازار» خارج شود.
            menu = get_crypto_analysis_keyboard(symbol)

            async def _smart_ai(base_txt: str, tf_name: str) -> tuple:
                """جمع‌بندی + راهنما دقیق‌تر بر اساس تایم‌فریم"""
                try:
                    from bot.services.ai_service import ask_ai
                    prompt = (
                        f"تو تحلیل‌گر ارشد مشتقات کریپتو هستی. تایم‌فریم تمرکز: {tf_name}.\n"
                        "فقط از داده زیر استفاده کن؛ عدد جعلی نساز.\n"
                        "خروجی دقیقاً:\n"
                        "جمع‌بندی: ۲ تا ۴ جمله فارسی (روند این تایم‌فریم، ساختار، مومنتوم، سیگنال)\n"
                        "راهنما: ۱ تا ۲ جمله (ورود الان / صبر / فرصت گذشته)\n"
                        "بدون بولت، بدون تضمین سود.\n\n"
                        + (base_txt or "")[:3000]
                    )
                    answer, _ = await ask_ai(query.from_user.id, prompt)
                    raw = (answer or "").strip()
                    summary, guide = "", ""
                    if "راهنما:" in raw:
                        a, b = raw.split("راهنما:", 1)
                        summary = a.replace("جمع‌بندی:", "").strip().replace("\n", " ")
                        guide = b.strip().replace("\n", " ")
                    elif "جمع‌بندی:" in raw:
                        summary = raw.split("جمع‌بندی:", 1)[-1].strip().replace("\n", " ")
                    else:
                        summary = raw.replace("\n", " ")
                    if len(summary) > 320:
                        summary = summary[:320].rsplit(" ", 1)[0] + "…"
                    if len(guide) > 220:
                        guide = guide[:220].rsplit(" ", 1)[0] + "…"
                    return summary, guide
                except Exception:
                    return "", ""

            def _split_telegram_text(txt: str, limit: int = 3900):
                """Split long Telegram messages without losing whole analysis sections.

                Telegram text messages are limited to 4096 chars and captions to 1024.
                We keep a safety margin and prefer line/section boundaries.
                """
                raw = (txt or "").strip()
                if not raw:
                    return []
                chunks = []
                current = ""
                for line in raw.splitlines():
                    candidate = line if not current else current + "\n" + line
                    if len(candidate) <= limit:
                        current = candidate
                        continue
                    if current:
                        chunks.append(current)
                        current = ""
                    if len(line) <= limit:
                        current = line
                        continue
                    # Extremely long AI line: strip HTML tags before hard-splitting so
                    # a partial <b>...</b> tag can never corrupt Telegram parsing.
                    plain = re.sub(r"<[^>]*>", "", line)
                    plain = html.unescape(plain)
                    while len(plain) > limit:
                        chunks.append(plain[:limit].rstrip())
                        plain = plain[limit:]
                    current = plain
                if current:
                    chunks.append(current)
                return chunks

            async def _send_full_text(txt: str, *, reply_to=None, reply_markup=None):
                """Send the complete analysis as one or more Telegram messages."""
                chunks = _split_telegram_text(txt)
                if not chunks:
                    return
                target = reply_to or query.message
                for i, chunk in enumerate(chunks):
                    kwargs = {"text": chunk, "parse_mode": "HTML"}
                    if i == len(chunks) - 1 and reply_markup is not None:
                        kwargs["reply_markup"] = reply_markup
                    await target.reply_text(**kwargs)

            async def _update_market_analysis_text(full_text: str):
                """متن تحلیل جدا از عکس؛ کیبورد همیشه زیر آخرین پیام تحلیل قرار می‌گیرد."""
                ids = list(context.user_data.get("market_analysis_text_ids") or [])
                chat_id = context.user_data.get("market_analysis_chat_id") or query.message.chat_id
                chunks = _split_telegram_text(full_text, limit=3900) or ["داده کافی نیست."]
                bot = context.bot
                if ids:
                    try:
                        await bot.edit_message_text(
                            chat_id=chat_id, message_id=ids[0], text=chunks[0],
                            parse_mode="HTML", reply_markup=None
                        )
                    except Exception:
                        pass
                    for old_id in ids[1:]:
                        try:
                            await bot.delete_message(chat_id=chat_id, message_id=old_id)
                        except Exception:
                            pass
                else:
                    m = await bot.send_message(chat_id=chat_id, text=chunks[0], parse_mode="HTML")
                    ids = [m.message_id]
                for chunk in chunks[1:]:
                    m = await bot.send_message(chat_id=chat_id, text=chunk, parse_mode="HTML")
                    ids.append(m.message_id)
                # فقط آخرین/آخرین تکه دکمه‌ها را داشته باشد؛ نه عکس و نه متن اول.
                for old_id in ids[:-1]:
                    try:
                        await bot.edit_message_reply_markup(chat_id=chat_id, message_id=old_id, reply_markup=None)
                    except Exception:
                        pass
                try:
                    await bot.edit_message_reply_markup(chat_id=chat_id, message_id=ids[-1], reply_markup=menu)
                except Exception:
                    pass
                context.user_data["market_analysis_text_ids"] = ids
                context.user_data["market_analysis_chat_id"] = chat_id

            async def _edit_photo_caption(png: bytes | None, caption: str):
                """نمودار را روی همان پیام به‌روزرسانی کن؛ کیبورد فقط زیر متن تحلیل باشد."""
                msg = query.message
                full_input = (caption or "📈 نمودار تحلیل").strip()
                if len(full_input) > 1000 or "━━━━━━━━━━━━━━━━━━━━" in full_input or "تحلیل هوشمند" in full_input:
                    try:
                        await _update_market_analysis_text(full_input)
                    except Exception as _txt_exc:
                        logger.debug("market analysis text update: %s", _txt_exc)
                cap = full_input.split("\n━━━━━━━━━━━━━━━━━━━━", 1)[0].strip()[:1000]
                try:
                    # دکمه‌ها زیر متن هستند؛ بنابراین callback معمولاً از پیام متن می‌آید.
                    # شناسه عکس قبلاً ذخیره شده و همان عکس را ویرایش می‌کنیم.
                    photo_msg_id = context.user_data.get("market_chart_message_id")
                    chat_id = context.user_data.get("market_chart_chat_id") or msg.chat_id
                    if msg.photo:
                        photo_msg_id = msg.message_id
                        chat_id = msg.chat_id
                    if photo_msg_id:
                        if png:
                            bio = BytesIO(png)
                            bio.name = f"{symbol}_chart.png"
                            media = InputMediaPhoto(media=bio, caption=cap, parse_mode="HTML")
                            await context.bot.edit_message_media(
                                chat_id=chat_id, message_id=photo_msg_id, media=media, reply_markup=None
                            )
                        else:
                            await context.bot.edit_message_caption(
                                chat_id=chat_id, message_id=photo_msg_id,
                                caption=cap, parse_mode="HTML", reply_markup=None
                            )
                        return
                    # اگر عکس شناسه نداشت، متن callback را دست‌کاری نکن؛ تحلیل متن قبلاً آپدیت شده است.
                except Exception as exc:
                    logger.warning("market chart same-message edit failed: %s", exc)

            async def _edit_text(txt: str):
                """Edit first message and send remaining chunks; never truncate at 4000."""
                text = (txt or "").strip()
                msg = query.message
                chunks = _split_telegram_text(text)
                if not chunks:
                    chunks = ["داده کافی نیست."]
                try:
                    if msg.photo:
                        # عکس فقط نمودار است؛ دکمه‌ها زیر متن تحلیل قرار می‌گیرند.
                        await msg.edit_caption(caption=msg.caption or "📈 نمودار تحلیل", parse_mode="HTML", reply_markup=None)
                        await _update_market_analysis_text(text)
                    else:
                        await _update_market_analysis_text(text)
                except Exception:
                    try:
                        await _send_full_text(text, reply_to=msg, reply_markup=menu)
                    except Exception as _exc:
                        logger.debug("%s: %s", __name__, _exc)

            if action == "gold":
                txt = await analyze_gold("1h")
                try:
                    png, _cap = await get_gold_chart("1h")
                except Exception:
                    png = None
                await _edit_photo_caption(png, "🥇 <b>تحلیل طلا / XAUUSD — 1H</b>\n━━━━━━━━━━━━━━━━━━━━\n" + (txt or "داده کافی نیست."))
                return

            if action == "ai" and symbol.lower() in ("gold", "xau", "xauusd", "xau/usd"):
                base = await analyze_gold("1h")
                from bot.services.ai_service import ask_ai
                prompt = (
                    "تو تحلیل‌گر ارشد XAU/USD هستی. فقط از داده‌های گزارش زیر استفاده کن و هیچ عددی را حدس نزن. "
                    "گزارش تلگرام‌پسند، بدون جدول Markdown و با تیترهای واضح بده. ساختار، HH/HL/LH/LL، BOS/CHOCH، "
                    "کندل و rejection، حمایت/مقاومت همان 1H، عرضه/تقاضا، نقدینگی، breakout/retest، RSI/ADX/ATR، حجم، "
                    "MTF، سناریوی Long، سناریوی Short، invalidation و نتیجه نهایی را پوشش بده. در صورت تناقض یا نبود داده، ورود را تأیید نکن.\n\n"
                    + (base or "")[:12000]
                )
                answer, _ = await ask_ai(query.from_user.id, prompt)
                safe_answer = html.escape((answer or "داده کافی برای تحلیل هوشمند طلا وجود ندارد.").strip())
                out = "🧠 <b>تحلیل هوشمند XAU/USD</b>\n━━━━━━━━━━━━━━━━━━━━\n" + safe_answer
                png, _cap = await get_gold_chart("1h")
                await _edit_photo_caption(png, out)
                return

            if action == "ai":
                # گزارش هوشمند باید کل داده قابل‌استفاده را تحلیل کند، نه اینکه آن را به جدول تبدیل کند.
                base = await analyze_crypto(symbol, timeframe="4h")
                from bot.services.ai_service import ask_ai
                prompt = (
                    "تو تحلیل‌گر ارشد Price Action و بازارهای مالی هستی. داده‌های زیر از منابع زنده سیستم آمده‌اند. "
                    "همه داده‌های موجود را بررسی کن و هیچ قیمت، سطح یا درصدی را حدس نزن. "
                    "خروجی را برای Telegram و به‌صورت گزارش خوانا بنویس؛ جدول Markdown نساز. "
                    "بخش‌ها: وضعیت بازار، ساختار HH/HL/LH/LL، BOS/CHOCH، کندل‌ها و rejection، حمایت/مقاومت همان تایم‌فریم، "
                    "عرضه/تقاضا، نقدینگی و Equal High/Low، شکست و retest، RSI/ADX/ATR، حجم، واگرایی، Funding/OI/Long-Short، "
                    "MTF، سناریوی Long، سناریوی Short، invalidation، و نتیجه نهایی. اگر داده‌ای نیست صریح بگو. "
                    "از عبارت‌های کوتاه و تیترهای واضح استفاده کن. در بازار ضعیف یا متناقض، ورود را تأیید نکن.\n\n" + base[:12000]
                )
                answer, _ = await ask_ai(query.from_user.id, prompt)
                safe_answer = html.escape((answer or "داده کافی برای تحلیل هوشمند وجود ندارد.").strip())
                out = "🧠 <b>تحلیل هوشمند حرفه‌ای</b>\n━━━━━━━━━━━━━━━━━━━━\n" + safe_answer
                # تحلیل AI روی 4H است؛ نمودار هم دقیقاً 4H باشد.
                png, _cap = await get_crypto_chart(symbol, 30)
                await _edit_photo_caption(png, out)
                return

            if action == "pa":
                if symbol.lower() in ("gold", "xau", "xauusd", "xau/usd"):
                    txt = await analyze_gold("1h")
                    png, _ = await get_gold_chart("1h")
                    await _edit_photo_caption(png, "🧠 <b>تحلیل پرایس اکشن طلا / XAUUSD — 1H</b>\n━━━━━━━━━━━━━━━━━━━━\n" + (txt or "داده کافی نیست."))
                else:
                    txt = await analyze_crypto(symbol, timeframe="4h")
                    png, _ = await get_crypto_chart(symbol, 30)
                    await _edit_photo_caption(png, "🧠 <b>تحلیل پرایس اکشن</b>\n━━━━━━━━━━━━━━━━━━━━\n" + (txt or "داده کافی نیست."))
                return

            if action == "15m":
                if symbol.lower() in ("gold", "xau", "xauusd", "xau/usd"):
                    txt = await analyze_gold("15m")
                    png, _ = await get_gold_chart("15m")
                    await _edit_photo_caption(png, "🥇 <b>تحلیل طلا / XAUUSD — 15M</b>\n━━━━━━━━━━━━━━━━━━━━\n" + (txt or "داده کافی نیست."))
                else:
                    await _edit_text("⚠️ تایم‌فریم 15M در این بخش فقط برای XAU/USD فعال است.")
                return

            if action == "day":
                # برای طلا: روزانه از XAU/USD همان تایم‌فریم؛ برای کریپتو همان مسیر قبلی
                if symbol.lower() in ("gold", "xau", "xauusd", "xau/usd"):
                    base = await analyze_gold("1d")
                    png, _ = await get_gold_chart("1d")
                    await _edit_photo_caption(png, "🥇 <b>تحلیل طلا / XAUUSD — 1D</b>\n━━━━━━━━━━━━━━━━━━━━\n" + (base or "داده کافی نیست."))
                    return
                # تحلیل روزانه + نمودار روزانه روی همان پیام
                base = await analyze_crypto(symbol, timeframe="1d")
                report = base
                png, _cap = await get_crypto_chart(symbol, 90)
                await _edit_photo_caption(png, report or "داده کافی نیست.")

            elif action == "hr":
                if symbol.lower() in ("gold", "xau", "xauusd", "xau/usd"):
                    base = await analyze_gold("1h")
                    png, _ = await get_gold_chart("1h")
                    await _edit_photo_caption(png, "🥇 <b>تحلیل طلا / XAUUSD — 1H</b>\n━━━━━━━━━━━━━━━━━━━━\n" + (base or "داده کافی نیست."))
                    return
                base = await analyze_crypto(symbol, timeframe="1h")
                report = base
                png, _cap = await get_crypto_chart(symbol, 7)
                await _edit_photo_caption(png, report or "داده کافی نیست.")

            elif action == "rec":
                txt = await trading_recommendation(symbol)
                await _edit_text(txt)

            elif action == "der":
                txt = await derivatives_radar(symbol)
                await _edit_text(txt)

            elif action == "risk":
                txt = await risk_scenarios(symbol)
                await _edit_text(txt)

            elif action == "pos":
                context.user_data["waiting_for"] = "crypto_pos"
                await _edit_text(position_size_guide(symbol))

            elif action == "al":
                context.user_data["waiting_for"] = "crypto_alert"
                txt = await entry_alert_text(symbol)
                await _edit_text(txt)

            elif action == "scan":
                txt = await market_scanner(10)
                await _edit_text(txt)

            elif action == "ref":
                if symbol.lower() in ("gold", "xau", "xauusd", "xau/usd"):
                    base = await analyze_gold("4h")
                    png, _ = await get_gold_chart("4h")
                    await _edit_photo_caption(png, "🥇 <b>تحلیل طلا / XAUUSD — 4H</b>\n━━━━━━━━━━━━━━━━━━━━\n" + (base or "داده کافی نیست."))
                    return
                base = await analyze_crypto(symbol, timeframe="4h")
                report = base
                png, _ = await get_crypto_chart(symbol, 30)
                await _edit_photo_caption(png, report or "داده کافی نیست.")

            else:
                await _edit_text("❌ گزینه ناشناخته")
        except Exception as e:
            try:
                await query.message.reply_text(f"⚠️ خطا: {e}")
            except Exception as _exc:
                logger.debug("%s: %s", __name__, _exc)
        return

    # هر callback ناشناخته‌ای — حداقل spinner را قطع کن
    await _safe_answer(query)
