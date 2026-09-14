async def _handle_economic_calendar(query, update, context, data, user_id):
    """Extracted callback branch; preserves original behavior."""
    from bot.features.market.economic_calendar import (
        get_calendar_for_user, calendar_text, get_calendar_keyboard,
        get_settings_keyboard, get_lead_keyboard, get_tz_keyboard,
        get_event_keyboard, get_event, refresh_calendar, event_detail,
        ai_context, is_speech_event, fetch_speech_context, fetch_speech_context,
    )
    from bot.database import get_economic_calendar_preferences, set_economic_calendar_preferences

    async def _ec_load(uid, mode="today", impact="all", currency="", date_str=""):
        evs, tzn = await get_calendar_for_user(uid, mode, impact, currency, date_str)
        context.user_data["ec_events"] = {x["id"]: x for x in evs}
        return evs, tzn

    try:
        if data == "ec:today":
            _set_ec_view(context, mode="today", impact="all")
            events, tz_name = await _ec_load(user_id, "today", "all")
            await _safe_answer(query)
            await query.edit_message_text(calendar_text(events, title="تقویم اقتصادی امروز", tz_name=tz_name), parse_mode="HTML", reply_markup=get_calendar_keyboard(user_id, mode="today", impact="all", events=events, selected_date=datetime_now_date(tz_name)))
            return
        if data == "ec:tomorrow":
            _set_ec_view(context, mode="tomorrow", impact="all")
            events, tz_name = await _ec_load(user_id, "tomorrow", "all")
            await _safe_answer(query)
            await query.edit_message_text(calendar_text(events, title="تقویم اقتصادی فردا", tz_name=tz_name), parse_mode="HTML", reply_markup=get_calendar_keyboard(user_id, mode="tomorrow", impact="all", events=events, selected_date=datetime_now_date(tz_name, 1)))
            return
        if data == "ec:week":
            # دیگر کل هفته یک‌جا ریخته نمی‌شود؛ همان امروز
            _set_ec_view(context, mode="today", impact="all")
            events, tz_name = await _ec_load(user_id, "today", "all")
            await _safe_answer(query, "نمایش روزانه")
            await query.edit_message_text(
                calendar_text(events, title="تقویم اقتصادی امروز", tz_name=tz_name),
                parse_mode="HTML",
                reply_markup=get_calendar_keyboard(user_id, mode="today", impact="all", events=events),
            )
            return
        if data.startswith("ec:day:") or data.startswith("ec:nav:"):
            # ec:day:-1 | ec:day:+1 | ec:nav:2026-09-11:+1
            from bot.features.market.economic_calendar import _tz as _ec_tz
            p = get_economic_calendar_preferences(user_id)
            tz_name = p.get("timezone") or getattr(config, "TIMEZONE", "Asia/Tehran")
            tz = _ec_tz(tz_name)
            today_local = datetime.now(tz).date()
            base_date = today_local
            offset = 0
            try:
                if data.startswith("ec:nav:"):
                    # ec:nav:YYYY-MM-DD:+1
                    parts = data.split(":")
                    # ["ec", "nav", "YYYY-MM-DD", "+1"] but date has no colon
                    # callback is ec:nav:2026-09-11:+1 → split → ec, nav, 2026-09-11, +1
                    base_s = parts[2]
                    offset = int(parts[3])
                    y, m, d = [int(x) for x in base_s[:10].split("-")]
                    base_date = datetime(y, m, d).date()
                else:
                    offset = int(data.split(":", 2)[2])
                    base_date = today_local
            except Exception:
                offset = 0
                base_date = today_local
            target = base_date + timedelta(days=offset)
            day = target.strftime("%Y-%m-%d")
            if target == today_local:
                mode = "today"
                title = "تقویم اقتصادی امروز"
            elif target == today_local - timedelta(days=1):
                mode = "yesterday"
                title = "تقویم اقتصادی دیروز"
            elif target == today_local + timedelta(days=1):
                mode = "tomorrow"
                title = "تقویم اقتصادی فردا"
            else:
                mode = "today"
                title = f"تقویم اقتصادی {day}"
            _set_ec_view(context, mode=mode, impact="all", date_str=day)
            # برای روزهای آینده، یکبار force refresh تا پنجره آینده پر شود
            if target > today_local:
                try:
                    await refresh_calendar(force=True)
                except Exception:
                    pass
            events, tz_name = await _ec_load(user_id, mode, "all", date_str=day)
            await _safe_answer(query)
            text = calendar_text(events, title=title, tz_name=tz_name)
            if not events and target > today_local:
                text += "\n\nℹ️ <i>منبع داده هنوز رویدادی برای این روز ثبت نکرده یا هنوز منتشر نشده است.</i>"
            try:
                await query.edit_message_text(
                    text,
                    parse_mode="HTML",
                    reply_markup=get_calendar_keyboard(
                        user_id, mode=mode, impact="all", events=events, selected_date=day
                    ),
                )
            except Exception as edit_err:
                # Message is not modified و خطاهای مشابه نباید کل handler را بشکنند
                if "not modified" not in str(edit_err).lower():
                    raise
            return
        if data == "ec:impact:high":
            _set_ec_view(context, mode="today", impact="high")
            events, tz_name = await _ec_load(user_id, "today", "high")
            await _safe_answer(query, "فقط خبرهای مهم")
            await query.edit_message_text(calendar_text(events, title="خبرهای مهم اقتصادی امروز", tz_name=tz_name), parse_mode="HTML", reply_markup=get_calendar_keyboard(user_id, mode="today", impact="high", events=events, selected_date=datetime_now_date(tz_name)))
            return
        if data == "ec:impact:all":
            _set_ec_view(context, mode="today", impact="all")
            events, tz_name = await _ec_load(user_id, "today", "all")
            await _safe_answer(query)
            await query.edit_message_text(calendar_text(events, title="تقویم اقتصادی امروز", tz_name=tz_name), parse_mode="HTML", reply_markup=get_calendar_keyboard(user_id, mode="today", impact="all", events=events, selected_date=datetime_now_date(tz_name)))
            return
        if data.startswith("ec:cur:"):
            cur = data.split(":", 2)[2].upper()
            _set_ec_view(context, mode="today", impact="all", currency=cur)
            events, tz_name = await _ec_load(user_id, "today", "all", cur)
            await _safe_answer(query, f"فیلتر {cur}")
            await query.edit_message_text(calendar_text(events, title=f"خبرهای {cur} امروز", tz_name=tz_name), parse_mode="HTML", reply_markup=get_calendar_keyboard(user_id, mode="today", impact="all", currency=cur, events=events, selected_date=datetime_now_date(tz_name)))
            return
        if data == "ec:noop":
            await _safe_answer(query)
            return
        if data == "ec:refresh":
            await _safe_answer(query, "در حال بروزرسانی…")
            await refresh_calendar(force=True)
            events, tz_name = await _ec_load(user_id, "today", "all")
            await query.edit_message_text(
                calendar_text(events, title="تقویم اقتصادی امروز", tz_name=tz_name),
                parse_mode="HTML",
                reply_markup=get_calendar_keyboard(user_id, mode="today", impact="all", events=events, selected_date=datetime_now_date(tz_name)),
            )
            return
        if data.startswith("ec:date:"):
            selected_date = data.split(":", 2)[2]
            events, tz_name = await _ec_load(user_id, "today", "all", date_str=selected_date)
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
            events, tz_name = await _ec_load(
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
            events, tz_name = await _ec_load(
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
            events, tz_name = await _ec_load(user_id, "today", "all", date_str=date_str)
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
            events, tz_name = await _ec_load(
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
            events, tz_name = await _ec_load(
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
            events, tz_name = await _ec_load(
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
            events, tz_name = await _ec_load(user_id, "today", "all")
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
            events, tz_name = await _ec_load(user_id, "today", "all")
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
                "داده تقویم:\n" + context_text[:4000]
            )
            try:
                answer, provider = await ask_ai(user_id, prompt)
            except Exception as ai_err:
                logger.error("ec analyze ask_ai failed: %s", ai_err, exc_info=True)
                msg = str(ai_err).strip() or "سرویس AI پاسخ نداد"
                if len(msg) > 280:
                    msg = msg[:280] + "…"
                await query.message.reply_text(
                    "⚠️ تحلیل این خبر الان ممکن نیست.\n"
                    f"{msg}\n\n"
                    "اگر کلید AI تنظیم است، چند ثانیه بعد دوباره امتحان کنید."
                )
                return
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
            p = get_economic_calendar_preferences(user_id)
            tz_name = p["timezone"] or getattr(config, "TIMEZONE", "Asia/Tehran")
            # اول از اسنپ‌شات همان پیام؛ بعد از کش زنده
            snap = (context.user_data or {}).get("ec_events") or {}
            e = snap.get(event_id)
            if not e:
                events = await refresh_calendar()
                e = get_event(events, event_id)
                if e:
                    context.user_data["ec_events"] = {x["id"]: x for x in events}
            if not e:
                await _safe_answer(query, "این خبر دیگر در فهرست فعلی نیست. یک‌بار «بروزرسانی» بزنید.", show_alert=True)
                return
            await _safe_answer(query)
            await query.edit_message_text(event_detail(e, tz_name), parse_mode="HTML", reply_markup=get_event_keyboard(e["id"], e))
            return
        if data.startswith("ec:analyze:"):
            event_id = data.split(":", 2)[2]
            await _safe_answer(query, "در حال تحلیل…")
            try:
                p = get_economic_calendar_preferences(user_id)
                tz_name = p.get("timezone") or getattr(config, "TIMEZONE", "Asia/Tehran")

                e = None
                snap = (context.user_data or {}).get("ec_events") or {}
                if isinstance(snap, dict):
                    e = snap.get(event_id)
                if not e:
                    events = await refresh_calendar()
                    e = get_event(events, event_id)
                    if events:
                        context.user_data["ec_events"] = {x["id"]: x for x in events}
                if not e:
                    await (query.message or update.effective_message).reply_text(
                        "⚠️ این خبر پیدا نشد. یک‌بار بروزرسانی بزنید."
                    )
                    return

                from bot.services.ai_service import ask_ai
                try:
                    ctx = ai_context([e], tz_name)
                except Exception:
                    ctx = (
                        f"{e.get('title')} | {e.get('country')} | impact={e.get('impact')} | "
                        f"actual={e.get('actual')} forecast={e.get('forecast')} previous={e.get('previous')}"
                    )

                required_sections = [
                    "معنی خبر",
                    "کریپتو",
                    "دلار",
                    "طلا",
                    "سهام",
                    "اوراق",
                    "سناریو",
                    "جمع‌بندی",
                ]
                prompt = (
                    "نقش: تحلیل‌گر اقتصاد کلان.\n"
                    "قوانین سخت:\n"
                    "- فقط فارسی\n"
                    "- عدد جعلی نساز\n"
                    "- فارکس جفت‌ارز ننویس\n"
                    "- هیچ جمله یا تیتر ناتمام نگذار\n"
                    "- هر تیتر فقط یک‌بار بیاید\n"
                    "دقیقاً این ۸ بخش را به ترتیب و کامل بنویس "
                    "(اگر اثر ضعیف است بنویس «اثر مستقیم کم»):\n"
                    "معنی خبر:\n"
                    "کریپتو:\n"
                    "دلار/DXY:\n"
                    "طلا:\n"
                    "سهام:\n"
                    "اوراق و بازدهی:\n"
                    "سناریوی Actual در برابر Forecast:\n"
                    "جمع‌بندی:\n"
                    "هر بخش حداکثر ۲ جمله کامل. حتماً تا جمع‌بندی را تمام کن.\n\n"
                    "داده:\n" + ctx
                )

                try:
                    answer, _ = await ask_ai(user_id, prompt)
                except Exception as ai_err:
                    logger.error("ec analyze failed: %s", ai_err, exc_info=True)
                    await (query.message or update.effective_message).reply_text(
                        "⚠️ تحلیل ناموفق بود:\n" + str(ai_err)[:350]
                    )
                    return

                answer = (answer or "").strip() or "تحلیل در دسترس نیست."

                def _missing_sections(text: str) -> list[str]:
                    return [s for s in required_sections if s not in text]

                def _looks_cut(text: str) -> bool:
                    t = (text or "").strip()
                    if not t:
                        return True
                    if t[-1] not in ".!?…۔؟":
                        # جمله ناتمام یا قطع‌شده
                        if len(t) > 80:
                            return True
                    if t.endswith(("،", ":", "؛", "-", "—", "…")):
                        return True
                    return False

                # اگر بخش‌ها ناقص است یا متن قطع شده، یکبار ادامه بخواه
                missing = _missing_sections(answer)
                if missing or _looks_cut(answer):
                    try:
                        cont_prompt = (
                            "پاسخ قبلی ناقص بود. از همان‌جا که قطع شده ادامه بده و "
                            "هیچ بخشی از متن قبلی را تکرار نکن.\n"
                            "اگر تیتری جا مانده فقط همان‌ها را کامل بنویس:\n"
                            + "\n".join(f"- {m}" for m in (missing or required_sections[-4:]))
                            + "\nحتماً با «جمع‌بندی:» تمام کن.\n\n"
                            "--- انتهای پاسخ قبلی ---\n"
                            + answer[-700:]
                            + "\n--- ادامه از اینجا ---\n\n"
                            "داده:\n" + ctx
                        )
                        cont, _ = await ask_ai(user_id, cont_prompt)
                        cont = (cont or "").strip()
                        if cont:
                            # جلوگیری از تکرار تیتر اول اگر مدل دوباره از اول شروع کرد
                            if cont.startswith(answer[:40]):
                                answer = cont
                            else:
                                answer = (answer.rstrip() + "\n" + cont).strip()
                    except Exception as cont_err:
                        logger.debug("ec analyze continue failed: %s", cont_err)

                from html import escape as _esc

                def _split_ai_text(txt: str, limit: int = 3200):
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

                detail = event_detail(e, tz_name)
                kb = get_event_keyboard(e.get("id") or event_id, e)
                chunks = _split_ai_text(answer, 3000)
                msg_target = query.message or update.effective_message

                # پیام اول: جزئیات رویداد + بخش اول تحلیل (بدون برش وسط جمله)
                head = (
                    detail
                    + "\n\n🤖 <b>تحلیل هوشمند بازار</b>\n"
                    + "━━━━━━━━━━━━━━━━━━━━\n"
                )
                first_body = _esc(chunks[0], quote=False)
                first_msg = head + f"<blockquote>{first_body}</blockquote>"
                if len(chunks) > 1:
                    first_msg += f"\n\n<i>… ادامه در پیام بعدی (1/{len(chunks)})</i>"

                if len(first_msg) <= 4000:
                    try:
                        await query.edit_message_text(
                            first_msg, parse_mode="HTML", reply_markup=kb
                        )
                    except Exception:
                        plain = (
                            detail.replace("<b>", "").replace("</b>", "")
                            .replace("<i>", "").replace("</i>", "")
                            .replace("<code>", "").replace("</code>", "")
                            + "\n\n🤖 تحلیل هوشمند بازار\n━━━━━━━━━━━━━━━━━━━━\n"
                            + chunks[0]
                        )
                        await query.edit_message_text(plain[:4000], reply_markup=kb)
                else:
                    # جزئیات را نگه دار؛ تحلیل را جدا بفرست
                    try:
                        await query.edit_message_text(
                            detail, parse_mode="HTML", reply_markup=kb
                        )
                    except Exception:
                        pass
                    await msg_target.reply_text(
                        "🤖 <b>تحلیل هوشمند بازار</b>\n━━━━━━━━━━━━━━━━━━━━\n"
                        f"<blockquote>{first_body}</blockquote>",
                        parse_mode="HTML",
                    )

                # بقیه تحلیل کامل در پیام‌های بعدی — هیچ بخشی حذف نشود
                for idx, chunk in enumerate(chunks[1:], start=2):
                    continuation = (
                        f"🤖 <b>ادامه تحلیل ({idx}/{len(chunks)})</b>\n"
                        "━━━━━━━━━━━━━━━━━━━━\n"
                        f"<blockquote>{_esc(chunk, quote=False)}</blockquote>"
                    )
                    await msg_target.reply_text(continuation, parse_mode="HTML")
                return
            except Exception as err:
                logger.error("ec analyze outer: %s", err, exc_info=True)
                try:
                    await (query.message or update.effective_message).reply_text(
                        "⚠️ خطا در تحلیل:\n" + str(err)[:400]
                    )
                except Exception:
                    pass
                return
        if data.startswith("ec:speech:"):
            event_id = data.split(":", 2)[2]
            await _safe_answer(query, "در حال تهیه خلاصه سخنرانی…")
            try:
                msg_target = query.message or update.effective_message
                p = get_economic_calendar_preferences(user_id)
                tz_name = p.get("timezone") or getattr(config, "TIMEZONE", "Asia/Tehran")
                snap = (context.user_data or {}).get("ec_events") or {}
                e = snap.get(event_id) if isinstance(snap, dict) else None
                if not e:
                    events = await refresh_calendar()
                    e = get_event(events, event_id)
                if not e:
                    await msg_target.reply_text("⚠️ این سخنرانی در فهرست فعلی نیست.")
                    return
                from bot.services.ai_service import ask_ai
                title = str(e.get("title") or "")
                source_txt = ""
                try:
                    source_txt = await asyncio.to_thread(
                        fetch_speech_context, title, str(e.get("country") or "")
                    )
                except Exception as fe:
                    logger.debug("speech fetch failed: %s", fe)
                prompt = (
                    "تو خبرنگار اقتصادی هستی. فقط فارسی بنویس.\n"
                    f"رویداد: {title} | ارز: {e.get('country')} | زمان: {e.get('utc')}\n"
                )
                if source_txt:
                    prompt += (
                        "متن/خلاصه منبع عمومی زیر را مبنا قرار بده و نقل‌قول جعلی نساز:\n"
                        + source_txt[:1800]
                        + "\n\n"
                    )
                else:
                    prompt += (
                        "متن کامل سخنرانی در دسترس نبود. صریحاً بگو متن رسمی پیدا نشد "
                        "و فقط زمینه مورد انتظار بازار را محتاطانه بنویس؛ نقل‌قول جعلی نساز.\n\n"
                    )
                prompt += (
                    "ساختار:\n"
                    "۱) موضوع سخنرانی\n"
                    "۲) نکات کلیدی\n"
                    "۳) پیام برای طلا و کریپتو و دلار\n"
                    "۴) جمع‌بندی\n"
                    "حداکثر ۱۸۰۰ کاراکتر. بدون Markdown."
                )
                try:
                    answer, _ = await ask_ai(user_id, prompt)
                except Exception as ai_err:
                    await msg_target.reply_text(
                        "⚠️ خلاصه سخنرانی الان ممکن نیست.\n" + str(ai_err)[:300]
                    )
                    return
                detail = event_detail(e, tz_name)
                body = (answer or "").strip() or "خلاصه در دسترس نیست."
                combined = (
                    detail
                    + "\n\n🗣 <b>خلاصه سخنرانی</b>\n━━━━━━━━━━━━━━━━━━━━\n"
                    + "<blockquote>"
                    + __import__("html").escape(body, quote=False)
                    + "</blockquote>"
                )
                kb = get_event_keyboard(e.get("id") or event_id, e)
                if len(combined) > 4000:
                    combined = combined[:3990] + "…"
                try:
                    await query.edit_message_text(
                        combined, parse_mode="HTML", reply_markup=kb
                    )
                except Exception:
                    await msg_target.reply_text(
                        "🗣 خلاصه سخنرانی\n━━━━━━━━━━━━━━━━━━━━\n" + body[:3500]
                    )
                return
            except Exception as err:
                logger.error("ec speech summary failed: %s", err, exc_info=True)
                try:
                    await (query.message or update.effective_message).reply_text(
                        "⚠️ خطا در خلاصه سخنرانی:\n" + str(err)[:300]
                    )
                except Exception:
                    pass
                return
        if data == "ec:back":
            _set_ec_view(context, mode="today", impact="all")
            events, tz_name = await _ec_load(user_id, "today", "all")
            await _safe_answer(query)
            await query.edit_message_text(
                calendar_text(events, title="تقویم اقتصادی امروز", tz_name=tz_name),
                parse_mode="HTML",
                reply_markup=get_calendar_keyboard(
                    user_id, mode="today", impact="all", events=events,
                    selected_date=datetime_now_date(tz_name),
                ),
            )
            return
    except Exception as e:
        err_s = str(e).lower()
        # خطای بی‌ضرر تلگرام وقتی محتوا عوض نشده
        if "not modified" in err_s:
            try:
                await _safe_answer(query)
            except Exception:
                pass
            return
        logger.error("economic calendar callback failed: %s", e, exc_info=True)
        try:
            await _safe_answer(query, "⚠️ خطا در تقویم اقتصادی.", show_alert=True)
        except Exception:
            pass
        try:
            msg = str(e).strip() or "خطای ناشناخته"
            if len(msg) > 300:
                msg = msg[:300] + "…"
            if "AI" in msg or "api" in msg.lower() or "key" in msg.lower() or "مدل" in msg or "سرویس" in msg:
                user_msg = f"⚠️ تحلیل هوشمند الان در دسترس نیست.\n{msg}"
            else:
                user_msg = f"⚠️ موقتاً مشکلی در تقویم اقتصادی پیش آمد.\n{msg}"
            await query.message.reply_text(user_msg)
        except Exception:
            pass
        return
