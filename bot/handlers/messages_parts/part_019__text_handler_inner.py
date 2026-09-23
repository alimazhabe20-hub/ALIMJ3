from telegram import Update
from telegram.ext import ContextTypes

async def _text_handler_inner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name or "کاربر"

    # Global navigation rule: a real ReplyKeyboard button always cancels the
    # previous input mode first. This MUST run before downloader/AI/waiting
    # handlers so no feature can consume a menu label as user input.
    _cancel_previous_operation_if_menu_button(context, text)

    # V70 downloader: handle a URL only when it is actual input, never a menu
    # button.
    if await handle_downloader_url_v71(update, context, text):
        return
    # City lookup is used by several unrelated menus. A broken/locked SQLite
    # connection must never prevent ordinary ReplyKeyboard buttons from routing.
    try:
        city = get_user_city(user_id)
    except Exception as exc:
        city = "قم"
        logger.error(
            "user city lookup failed; continuing with fallback city=%r user_id=%s: %s",
            city, user_id, exc, exc_info=True,
        )
    try: auto_capture_memory(user_id, text)
    except Exception: pass
    waiting = context.user_data.get("waiting_for")
    # AI chat mode
    if context.user_data.get("ai_mode"):
        if _is_back(text) or _is_back_more(text):
            context.user_data.pop("ai_mode", None)
            context.user_data.pop("waiting_for", None)
            await update.message.reply_text("➕ منوی بیشتر:", reply_markup=get_more_keyboard())
            return
        if text.startswith(("➕", "🏠", "📅", "🕌", "💰", "🌤", "🛠", "🎮", "🎨", "👤", "🏙", "🌍", "🔙", "🤖")):
            if text != "🤖 دستیار هوشمند":
                context.user_data.pop("ai_mode", None)
                # fall through to normal menu handling
            else:
                # repeat the AI entry prompt
                providers = enabled_providers()
                provider_text = "، ".join(providers) if providers else "هیچ سرویس فعالی ندارد"
                await update.message.reply_text(
                    "🤖 دستیار هوشمند روز زیبا\n\n"
                    "پیامت را بفرست تا به هوش مصنوعی ارسال شود.\n"
                    f"سرویس‌های فعال: {provider_text}",
                    reply_markup=get_ai_keyboard(user_id),
                )
                return
        else:
            try:
                # فقط خواندن متن با ویس (بدون AI)
                import re as _re
                m_read = _re.match(r"^(بخون|بخوان)\s*[:：]?\s*(.+)$", text, _re.I | _re.S)
                if m_read:
                    to_read = m_read.group(2).strip()
                    try:
                        await _send_ai_voice(
                            update, to_read, user_id)
                    except Exception as ve:
                        await update.message.reply_text(f"⚠️ ویس ساخته نشد: {ve}")
                    return
                if looks_like_image_request(text):
                    notice = await update.message.reply_text("🎨 در حال ساخت تصویر...")
                    try:
                        img_bytes, mime = await generate_or_edit_image(text)
                        from io import BytesIO
                        bio = BytesIO(img_bytes)
                        bio.name = "ai_image.png" if "png" in mime else "ai_image.jpg"
                        await update.message.reply_photo(
                            photo=bio,
                            caption="🎨 تصویر ساخته شد",
                        )
                    finally:
                        try:
                            await notice.delete()
                        except Exception as _exc:
                            logger.debug("%s: %s", __name__, _exc)
                    return
                mode_msg = _apply_voice_chat_flags(context, text)
                if mode_msg:
                    await update.message.reply_text(mode_msg)
                # «ویس بفرست» بدون سؤال → آخرین جواب را با ویس بفرست
                if is_voice_only_request(text):
                    last = get_last_answer(user_id) or (context.user_data or {}).get("last_ai_answer")
                    if last:
                        try:
                            await _send_ai_voice(update, last, user_id)
                        except Exception as ve:
                            await update.message.reply_text(f"⚠️ ویس ساخته نشد: {ve}")
                    else:
                        await update.message.reply_text(
                            "هنوز جوابی برای خواندن ندارم. اول یک سؤال بپرس، بعد بگو «ویس بفرست»."
                        )
                    return
                voice_mode = wants_voice_reply(text) or bool(
                    context.user_data.get("ai_voice_chat")
                )
                ask_text = strip_voice_prefix(text) if wants_voice_reply(text) else text
                # اگر فقط روشن کردن حالت ویس بود و سؤال دیگری نبود، لازم نیست AI سنگین
                if mode_msg and wants_voice_chat_mode(text) and len(ask_text) < 40:
                    try:
                        await _send_ai_voice(
                            update,
                            "باشه، با ویس حرف می‌زنیم. هر وقت خواستی بگو.",
                            user_id,
                        )
                    except Exception as _exc:
                        logger.debug("%s: %s", __name__, _exc)
                    return
                # قابلیت‌های ویژه قبل از AI عمومی
                handled = await _handle_special_ai_intents(
                    update, context, user_id, ask_text
                )
                if handled:
                    return
                answer, provider = await _ask_ai_with_typing(
                    update, context, user_id, ask_text
                )
                if context.user_data is not None:
                    context.user_data["last_ai_answer"] = answer
                if not (context.user_data or {}).get("_ai_already_sent"):
                    await _send_ai_answer(update, user_id, answer, prompt=ask_text)
                if context.user_data is not None:
                    context.user_data.pop("_ai_already_sent", None)
                explicit = wants_voice_reply(text)
                if should_auto_voice_reply(
                    ask_text,
                    answer,
                    input_was_voice=False,
                    explicit_voice=explicit,
                    voice_chat_mode=bool(context.user_data.get("ai_voice_chat")),
                ):
                    try:
                        await _send_ai_voice(
                            update, answer, user_id
                        )
                    except Exception as ve:
                        await update.message.reply_text(
                            "⚠️ متن آماده شد ولی ویس ساخته نشد. لطفاً دوباره امتحان کنید."
                        )
            except Exception as exc:
                logger.error("AI request failed: %s", exc, exc_info=True)
                await update.message.reply_text(
                    "⚠️ فعلاً سرویس هوش مصنوعی پاسخ نداد. چند ثانیه بعد دوباره امتحان کنید."
                )
            return
    if waiting:
        if _is_back(text) or _is_back_more(text):
            context.user_data.pop("waiting_for", None)
            await update.message.reply_text("➕ منوی بیشتر:", reply_markup=get_more_keyboard())
            return
        # اگر کاربر دکمه منو زد، waiting را رها کن و ادامه بده
        menu_starts = (
            "➕", "🏠", "📅", "🕌", "💰", "🌤", "🛠", "🎮", "🎨", "👤",
            "🏙", "🌍", "🔙", "💵", "💎", "🔄", "📈", "📐", "🔢", "🔐",
            "📝", "🗺", "⏰", "📒", "📖", "😂", "🧠", "💪", "💖", "🕋",
            "📿", "🙏", "🔔", "🌫", "📍", "🇬🇧", "🇮🇷", "🌈", "📋", "🤖", "🧹",
        )
        # Some important market/calendar buttons do not start with the emoji
        # prefixes above (notably 🗓 and 🥇). Keep a small explicit allow-list so
        # stale waiting states can never swallow a normal menu button.
        known_menu_buttons = {
            "🗓 تقویم اقتصادی", "📅 تقویم اقتصادی", "تقویم اقتصادی",
            "🥇 تحلیل طلا", "تحلیل طلا",
            "📊 نمودار و تحلیل ارز دیجیتال", "نمودار و تحلیل ارز دیجیتال",
            "📊 نمودار قیمت کریپتو", "نمودار قیمت کریپتو", "نمودار کریپتو",
            "🔍 تحلیل ارز دیجیتال", "تحلیل ارز دیجیتال", "تحلیل کریپتو",
            "🧠 تحلیل هوشمند حرفه‌ای", "تحلیل هوشمند حرفه‌ای",
            "🛒 دستیار خرید", "🛍 دستیار خرید", "دستیار خرید",
            "بیشتر", "بازار", "مذهبی", "ابزارها", "سرگرمی", "فونت", "پروفایل",
            "تاریخ و سن", "هوا و مکان", "انتخاب شهر", "تقویم", "زبان",
        }
        if text.startswith(menu_starts) or text in known_menu_buttons:
            context.user_data.pop("waiting_for", None)
            waiting = None
        else:
            handlers = {
                "date_convert": _h_date_convert, "age_calc": _h_age_calc,
                "birthday": _h_birthday, "zodiac": _h_zodiac, "lunar": _h_lunar,
                "date_diff": _h_date_diff, "age_diff": _h_age_diff,
                "event_search": _h_event_search, "countdown": _h_countdown,
                "calc": _h_calc,
                "profit": _h_profit, "currency": _h_currency, "distance": _h_distance, "crypto_chart": _h_crypto_full, "crypto_analyze": _h_crypto_full, "crypto_full": _h_crypto_full, "crypto_pos": _h_crypto_pos, "crypto_alert": _h_crypto_pos,
                "ict_analyze": _h_ict,
                "birth_save": _h_birth_save,
                "count_text": _h_count_text,
                "font_text": _h_font_text, "font_all": _h_font_all,
                "economic_calendar": _h_economic_calendar,
            }
            fn = handlers.get(waiting)
            if fn:
                try:
                    await fn(update, context, text, user_id)
                except Exception as e:
                    logger.error(f"waiting handler {waiting}: {e}", exc_info=True)
                    context.user_data.pop("waiting_for", None)
                    await update.message.reply_text(
                        "⚠️ خطا در پردازش. دوباره از منو انتخاب کنید.",
                        reply_markup=get_more_keyboard(),
                    )
                return
            context.user_data.pop("waiting_for", None)
    if text in ("🏙 انتخاب شهر", "انتخاب شهر"):
        await update.message.reply_text("🏙 کشور:", reply_markup=get_country_keyboard()); return
    if text in ("📅 تقویم", "تقویم"):
        t = get_today_tehran()
        await update.message.reply_text(get_calendar_text(t.year, t.month, t.day, user_id), reply_markup=get_calendar_buttons(t.year, t.month, t.day, user_id)); return
    if text in ("🌍 زبان", "زبان"):
        await update.message.reply_text("🌍 زبان:", reply_markup=get_language_keyboard()); return
    if text in ("➕ بیشتر", "بیشتر"):
        await update.message.reply_text("➕ بخش را انتخاب کنید:", reply_markup=get_more_keyboard()); return
    if text == "📥 دانلودر فایل":
        from bot.handlers.v71_handlers import downloader_entry_v71
        await downloader_entry_v71(update, context); return
    if text == "🤖 دستیار هوشمند":
        providers = enabled_providers()
        context.user_data["ai_mode"] = True
        provider_text = "، ".join(providers) if providers else "هیچ سرویس فعالی ندارد"
        await update.message.reply_text(
            "🤖 دستیار هوشمند روز زیبا\n\n"
            "پیامت را بفرست تا به هوش مصنوعی ارسال شود.\n"
            f"سرویس‌های فعال: {provider_text}",
            reply_markup=get_ai_keyboard(user_id),
        )
        return
    if text == "📅 تاریخ و سن":
        await update.message.reply_text("📅 تاریخ و سن:", reply_markup=get_date_tools_keyboard()); return
    if text == "🕌 مذهبی":
        await update.message.reply_text("🕌 مذهبی:", reply_markup=get_religious_keyboard()); return
    if text == "💰 بازار":
        await update.message.reply_text("💰 بازار:", reply_markup=get_market_keyboard()); return
    if text == "🌤 هوا و مکان":
        await update.message.reply_text("🌤 هوا و مکان:", reply_markup=get_weather_geo_keyboard()); return
    if text == "🛠 ابزارها":
        await update.message.reply_text("🛠 ابزارها:", reply_markup=get_tools_keyboard()); return
    if text == "🎮 سرگرمی":
        await update.message.reply_text("🎮 سرگرمی:", reply_markup=get_fun_keyboard()); return
    if text in ("🎨 فونت", "فونت"):
        await update.message.reply_text("🎨 بخش فونت:", reply_markup=get_font_keyboard()); return
    if text in ("📋 لیست فونت‌ها", "📋 لیست همه فونت‌ها"):
        await update.message.reply_text(list_fonts(), reply_markup=get_font_keyboard()); return
    if text == "🇬🇧 فونت انگلیسی":
        await update.message.reply_text("🇬🇧 یک فونت انگلیسی انتخاب کنید:", reply_markup=get_font_en_keyboard()); return
    if text == "🇮🇷 فونت فارسی":
        await update.message.reply_text("🇮🇷 یک فونت فارسی/تزئینی انتخاب کنید:", reply_markup=get_font_fa_keyboard()); return
    if text == "🌈 همه فونت‌ها":
        context.user_data["waiting_for"] = "font_all"
        await update.message.reply_text("🌈 یک کلمه یا جمله بفرستید تا روی همه فونت‌ها اعمال شود:", reply_markup=get_font_keyboard()); return
    if text == "🔙 بازگشت فونت":
        await update.message.reply_text("🎨 بخش فونت:", reply_markup=get_font_keyboard()); return
    # انتخاب فونت از نام نمایشی
    name_to_key = {v: k for k, v in FONT_NAMES.items()}
    name_to_key.update({v[:18]: k for k, v in FONT_NAMES.items()})
    if text in name_to_key or text in FONT_NAMES:
        key = name_to_key.get(text, text)
        context.user_data["selected_font"] = key
        context.user_data["waiting_for"] = "font_text"
        await update.message.reply_text(f"🎨 فونت انتخاب شد.\nمتن را بفرستید:", reply_markup=get_font_keyboard()); return
    if text == "👤 پروفایل":
        await update.message.reply_text("👤 پروفایل:", reply_markup=get_profile_keyboard()); return
    if _is_back_more(text):
        await update.message.reply_text("➕ منوی بیشتر:", reply_markup=get_more_keyboard()); return
    # تاریخ و سن
    if text in ("🔄 مبدل تاریخ", "مبدل تاریخ"):
        context.user_data["waiting_for"] = "date_convert"; track_usage(user_id, "date_convert")
        await update.message.reply_text("🔄 تاریخ:\n`1403/05/18` یا `2024/08/09`", reply_markup=get_date_tools_keyboard()); return
    if text in ("🎂 محاسبه سن", "🎂 محاسبه سن دقیق", "محاسبه سن"):
        context.user_data["waiting_for"] = "age_calc"; track_usage(user_id, "age_calc")
        await update.message.reply_text("🎂 تولد شمسی:\n`1375/03/15`", reply_markup=get_date_tools_keyboard()); return
    if text in ("🎉 روزشمار تولد", "روزشمار تولد"):
        context.user_data["waiting_for"] = "birthday"; track_usage(user_id, "birthday")
        bd = get_birth_date(user_id)
        if bd and len(bd.split("/")) == 3:
            p = bd.split("/"); context.user_data.pop("waiting_for", None)
            await update.message.reply_text(birthday_countdown(int(p[0]), int(p[1]), int(p[2])), reply_markup=get_date_tools_keyboard()); return
        await update.message.reply_text("🎉 تولد شمسی:\n`1375/03/15`", reply_markup=get_date_tools_keyboard()); return
    if text in ("♈ برج و حیوان", "برج و حیوان"):
        context.user_data["waiting_for"] = "zodiac"; track_usage(user_id, "zodiac")
        await update.message.reply_text("♈ تولد شمسی:\n`1375/03/15`", reply_markup=get_date_tools_keyboard()); return
    if text in ("🌙 سن قمری", "سن قمری"):
        context.user_data["waiting_for"] = "lunar"; track_usage(user_id, "lunar")
        await update.message.reply_text("🌙 تولد شمسی:\n`1375/03/15`", reply_markup=get_date_tools_keyboard()); return
    if text in ("📆 اختلاف تاریخ", "📆 اختلاف دو تاریخ", "اختلاف تاریخ"):
        context.user_data["waiting_for"] = "date_diff"; track_usage(user_id, "date_diff")
        await update.message.reply_text(
            "📆 دو تاریخ شمسی بفرست:\n"
            "`1375/03/15 1403/05/18`\n\n"
            "خروجی: سال/ماه/روز • هفته • ساعت • روز کاری • میلادی و قمری",
            reply_markup=get_date_tools_keyboard(),
        ); return
    if text in ("👥 اختلاف سن", "اختلاف سن"):
        context.user_data["waiting_for"] = "age_diff"; track_usage(user_id, "age_diff")
        await update.message.reply_text(
            "👥 دو تاریخ تولد شمسی بفرست:\n"
            "`1375/03/15 1380/06/20`\n\n"
            "خروجی: سن هر نفر • اختلاف دقیق • سن قمری • نسبت سنی",
            reply_markup=get_date_tools_keyboard(),
        ); return
    if text in ("📅 تقویم ماه", "تقویم ماه"):
        track_usage(user_id, "month_cal")
        await update.message.reply_text(month_calendar(), reply_markup=get_date_tools_keyboard()); return
    if text in ("🔍 مناسبت‌یاب", "مناسبت‌یاب"):
        context.user_data["waiting_for"] = "event_search"; track_usage(user_id, "event_search")
        await update.message.reply_text("🔍 کلمه کلیدی:\n`نوروز`", reply_markup=get_date_tools_keyboard()); return
    if text in ("🌸 شمارش نوروز", "شمارش نوروز"):
        track_usage(user_id, "nowruz")
        await update.message.reply_text(nowruz_countdown(), reply_markup=get_date_tools_keyboard()); return
    if text in ("🌍 ساعت جهانی", "ساعت جهانی"):
        track_usage(user_id, "world_clock")
        await update.message.reply_text(world_clock(), reply_markup=get_date_tools_keyboard()); return
    if text in ("⏳ شمارش‌معکوس", "شمارش‌معکوس"):
        context.user_data["waiting_for"] = "countdown"; track_usage(user_id, "countdown")
        await update.message.reply_text("⏳ تاریخ:\n`1405/01/01 نوروز`", reply_markup=get_date_tools_keyboard()); return
    # مذهبی
    if text in ("🕋 قبله‌نما", "قبله‌نما"):
        track_usage(user_id, "qibla")
        await update.message.reply_text(qibla_direction(city), reply_markup=get_religious_keyboard()); return
    if text in ("📿 اذکار روز", "اذکار روز"):
        track_usage(user_id, "adhkar")
        await update.message.reply_text(daily_adhkar(user_id), reply_markup=get_religious_keyboard()); return
    if text in ("📖 آیه و حدیث", "آیه و حدیث"):
        track_usage(user_id, "verse")
        await update.message.reply_text(await daily_verse_hadith(user_id), reply_markup=get_religious_keyboard()); return
    if text in ("🕌 مناسبت مذهبی", "مناسبت مذهبی"):
        track_usage(user_id, "rel_cd")
        # معماری مشابه تقویم: نمای کلی + مناسبت‌های نزدیک + نمای ماه جاری قمری
        body = religious_countdown()
        body += "\n\n" + "—" * 12 + "\n" + religious_month_view()
        await update.message.reply_text(body, reply_markup=get_religious_keyboard()); return
    if text in ("🙏 استخاره", "استخاره"):
        track_usage(user_id, "istikhara")
        context.user_data["waiting_for"] = "istikhara_confirm"
        await update.message.reply_text(istikhara_intro(), reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("🙏 استخاره بگیر")], [KeyboardButton("🔙 بازگشت به مذهبی")]],
            resize_keyboard=True
        )); return
    if text == "🙏 استخاره بگیر":
        context.user_data.pop("waiting_for", None)
        track_usage(user_id, "istikhara_do")
        await update.message.reply_text(await istikhara(user_id), reply_markup=get_religious_keyboard()); return
    if text == "🔙 بازگشت به مذهبی":
        context.user_data.pop("waiting_for", None)
        await update.message.reply_text("🕌 مذهبی:", reply_markup=get_religious_keyboard()); return
    if text in ("🔔 تنظیم اذان", "تنظیم اذان"):
        track_usage(user_id, "azan")
        await _show_azan_settings(update, user_id, city)
        return
    # دکمه‌های شخصی‌سازی اذان
    if text in ("🔔 اعلان‌ها: روشن", "🔕 اعلان‌ها: خاموش"):
        settings = get_azan_settings(user_id)
        set_azan_master(user_id, not settings["enabled"])
        await _show_azan_settings(update, user_id, city, note="وضعیت کلی اعلان‌ها تغییر کرد.")
        return
    if text in ("🔄 همه روشن",):
        set_azan_master(user_id, True)
        for key in ("fajr", "dhuhr", "asr", "maghrib", "isha"):
            field = f"notify_{key}"
            update_user_field(user_id, field, 1)
        await _show_azan_settings(update, user_id, city, note="همه اذان‌ها روشن شدند.")
        return
    if text in ("⏹ همه خاموش",):
        for key in ("fajr", "dhuhr", "asr", "maghrib", "isha"):
            update_user_field(user_id, f"notify_{key}", 0)
        await _show_azan_settings(update, user_id, city, note="همه اذان‌ها خاموش شدند.")
        return
    # تحلیل طلا دقیقاً داخل همان جریان «بازار» و با ساختار منوی تحلیل کریپتو
    # نمایش داده می‌شود؛ وارد بخش/منوی جدید نمی‌شود.
    if text in ("🥇 تحلیل طلا", "تحلیل طلا"):
        try:
            track_usage(user_id, "gold_analysis")
            notice = await update.message.reply_text("⏳ در حال دریافت تحلیل زنده طلا / XAUUSD…")
            report = await analyze_gold("1h")
            try:
                png, _ = await get_gold_chart("1h")
            except Exception:
                png = None
            try:
                await notice.delete()
            except Exception:
                pass
            # XAUUSD همان منوی Inline تحلیل کریپتو را با نماد gold استفاده می‌کند.
            # بنابراین تایم‌فریم، پرایس‌اکشن، تحلیل هوشمند و بروزرسانی همگی روی همان پیام می‌مانند.
            menu = get_crypto_analysis_keyboard("gold")
            if png:
                from io import BytesIO
                bio = BytesIO(png)
                bio.name = "gold_xauusd_1h.png"
                chart_msg = await update.message.reply_photo(
                    photo=bio,
                    caption="🥇 <b>تحلیل طلا / XAUUSD — 1H</b>",
                    parse_mode="HTML",
                )
                context.user_data["market_chart_message_id"] = chart_msg.message_id
                context.user_data["market_chart_chat_id"] = update.effective_chat.id
            chunks = [report[i:i+3900] for i in range(0, len(report or ""), 3900)] or ["داده کافی برای تحلیل طلا در دسترس نیست."]
            text_ids = []
            for i, chunk in enumerate(chunks):
                mtxt = await update.message.reply_text(
                    chunk, parse_mode="HTML",
                    reply_markup=menu if i == len(chunks) - 1 else None,
                )
                text_ids.append(mtxt.message_id)
            context.user_data["market_analysis_text_ids"] = text_ids
            context.user_data["market_analysis_chat_id"] = update.effective_chat.id
            return
        except Exception as exc:
            logger.error("gold market button failed: %s", exc, exc_info=True)
            await update.message.reply_text(
                "⚠️ دریافت تحلیل طلا موقتاً ناموفق بود؛ دوباره تلاش کنید.",
                reply_markup=get_market_keyboard(),
            )
            return
    # تحلیل مستقیم طلا: کاربر می‌تواند فقط «gold»، «طلا»، «اونس»، «XAUUSD» یا عبارت تحلیلی مشابه را بفرستد.
    # این مسیر قبل از fallback عمومی اجرا می‌شود تا Gold هرگز به‌عنوان «نماد نامعتبر» پاسخ داده نشود.
    _gold_text = re.sub(r"[\s\u200c_/\-]+", "", text.lower())
    _gold_aliases = ("gold", "xau", "xauusd", "طلا", "طلایجهانی", "اونس", "اونسجهانی")
    if any(alias in _gold_text for alias in _gold_aliases):
        # فقط وقتی پیام واقعاً درباره طلاست؛ اعداد/متن‌های نامرتبطی که کلمه gold را داخل جمله دارند هم به تحلیل طلا می‌روند.
        try:
            track_usage(user_id, "gold_analysis")
            notice = await update.message.reply_text("⏳ در حال دریافت تحلیل زنده طلا / XAUUSD…")
            report = await analyze_gold("1h")
            try:
                png, _ = await get_gold_chart("1h")
            except Exception:
                png = None
            try:
                await notice.delete()
            except Exception:
                pass
            if png:
                from io import BytesIO
                bio = BytesIO(png)
                bio.name = "gold_xauusd_1h.png"
                chart_msg = await update.message.reply_photo(
                    photo=bio,
                    caption="🥇 Gold / XAUUSD — 1H",
                )
                context.user_data["market_chart_message_id"] = chart_msg.message_id
                context.user_data["market_chart_chat_id"] = update.effective_chat.id
            # گزارش کامل را به‌صورت پیام متنی می‌فرستیم تا محدودیت 1024 کاراکتری کپشن باعث ناقص شدن تحلیل نشود.
            chunks = [report[i:i+3900] for i in range(0, len(report or ""), 3900)] or ["داده کافی برای تحلیل طلا در دسترس نیست."]
            text_ids = []
            for chunk in chunks:
                try:
                    mtxt = await update.message.reply_text(chunk, parse_mode="HTML")
                except Exception:
                    mtxt = await update.message.reply_text(re.sub(r"<[^>]+>", "", chunk)[:3500])
                text_ids.append(mtxt.message_id)
            context.user_data["market_analysis_text_ids"] = text_ids
            context.user_data["market_analysis_chat_id"] = update.effective_chat.id
            return
        except Exception as exc:
            logger.error("direct gold analysis failed: %s", exc, exc_info=True)
            await update.message.reply_text("⚠️ دریافت تحلیل طلا موقتاً ناموفق بود؛ دوباره تلاش کنید.")
            return
    # دکمه‌های تکی اذان (با ✅ یا ❌)
    _azan_btn_map = {
        "اذان صبح": "fajr",
        "اذان ظهر": "dhuhr",
        "اذان عصر": "asr",
        "اذان مغرب": "maghrib",
        "اذان عشاء": "isha",
    }
    for label, key in _azan_btn_map.items():
        if text.endswith(label) and (text.startswith("✅") or text.startswith("❌")):
            new_state = toggle_azan_prayer(user_id, key)
            status = "روشن" if new_state else "خاموش"
            await _show_azan_settings(update, user_id, city, note=f"{label} {status} شد.")
            return
    if text in ("🔙 بازگشت به مذهبی",):
        await update.message.reply_text("🕌 مذهبی:", reply_markup=get_religious_keyboard())
        return
    # «دستیار خرید» قدیمی حذف شده؛ خرید اکنون بخشی از همان دستیار هوشمند است.
    if text in ("🛒 دستیار خرید", "دستیار خرید", "🛍 دستیار خرید"):
        context.user_data["ai_mode"] = True
        context.user_data.pop("ai_shopping_mode", None)
        await update.message.reply_text(
            "🤖 دستیار هوشمند فعال است.\n\n"
            "اسم محصول، قیمت، لینک خرید یا عکس محصول را بفرست؛ خودم جستجوی فروشگاهی و مقایسه را انجام می‌دهم.",
        )
        return
    if text in ("💵 قیمت کامل بازار", "قیمت کامل بازار"):
        track_usage(user_id, "market")
        m = await update.message.reply_text("⏳ دریافت قیمت‌ها...")
        r = await full_market_prices()
        await m.edit_text(r)
        await update.message.reply_text("💰", reply_markup=get_market_keyboard()); return
    if text in ("💎 ۲۰ ارز برتر کریپتو", "۲۰ ارز برتر کریپتو", "💎 ۳۰۰ ارز برتر کریپتو", "۳۰۰ ارز برتر کریپتو", "کریپتو"):
        track_usage(user_id, "crypto_top")
        m = await update.message.reply_text("⏳ دریافت لیست کریپتو...")
        r = await get_top_crypto(20)
        await m.edit_text(r)
        await update.message.reply_text("💎", reply_markup=get_market_keyboard()); return
    if text in ("🔄 تبدیل ارز", "تبدیل ارز", "🔄 تبدیل ارز / کریپتو", "تبدیل ارز / کریپتو"):
        context.user_data["waiting_for"] = "currency"; track_usage(user_id, "currency")
        await update.message.reply_text(
            "🔄 مبدل هوشمند ارز / کریپتو\n\n"
            "تقریباً همه ارزهای دیجیتال + تومان/دلار پشتیبانی می‌شود.\n\n"
            "مثال‌ها:\n"
            "• 1.5 btc\n"
            "• 20 ton\n"
            "• 100 تتر\n"
            "• 50 دلار\n"
            "• 1 btc eth\n"
            "• 50000 تومان دلار\n"
            "• 100 usdt toman\n"
            "• ۲ بیتکوین",
            reply_markup=get_market_keyboard()
        ); return
    if text in ("🗓 تقویم اقتصادی", "تقویم اقتصادی", "📅 تقویم اقتصادی"):
        track_usage(user_id, "economic_calendar")
        await _h_economic_calendar(update, context, text, user_id)
        return
    if text in ("📈 سود و ضرر", "سود و ضرر"):
        context.user_data["waiting_for"] = "profit"; track_usage(user_id, "profit")
        await update.message.reply_text("📈 `1000 1200` یا `1000 1200 5`", reply_markup=get_market_keyboard()); return
    if text in ("📐 تحلیل ICT", "تحلیل ICT", "ICT", "ict"):
        await _h_ict(update, context, text, user_id)
        return
    if text in ("🧠 کدوم ارز بخرم؟", "کدوم ارز بخرم؟", "کدام ارز بخرم؟"):
        from bot.features.market.crypto_opportunity import opportunity_timeframe_keyboard
        track_usage(user_id, "crypto_opportunity")
        await update.message.reply_text(
            "🧠 <b>کدوم ارز بخرم؟</b>\n\n"
            "تایم‌فریم را انتخاب کن. بعد از انتخاب، جامعه ۵۰۰ ارز برتر بررسی می‌شود و ۵ ستاپ دارای سیگنال لانگ/شورت با تحلیل حرفه‌ای نمایش داده می‌شود.",
            parse_mode="HTML",
            reply_markup=opportunity_timeframe_keyboard(),
        )
        return
    if text in (
        "📊 نمودار و تحلیل ارز دیجیتال",
        "نمودار و تحلیل ارز دیجیتال",
        "📊 نمودار قیمت کریپتو",
        "نمودار قیمت کریپتو",
        "نمودار کریپتو",
        "🔍 تحلیل ارز دیجیتال",
        "تحلیل ارز دیجیتال",
        "تحلیل کریپتو",
    ):
        context.user_data["waiting_for"] = "crypto_full"
        track_usage(user_id, "crypto_full")
        await update.message.reply_text(
            "📈 تحلیل‌گر هوشمند کریپتو\n"
            "────────────────────\n\n"
            "نماد را بفرستید. بازه نمودار اختیاری است:\n\n"
            "مثال‌ها:\n"
            "• btc — بیت‌کوین (۳۰ روز)\n"
            "• eth 30 — اتریوم، ۳۰ روز\n"
            "• sol 7 — سولانا، ۷ روز\n"
            "• ton — تون\n\n"
            "📦 در یک پیام دریافت می‌کنید:\n"
            "• نمودار چندپنلی (کندل، EMA، بولینگر، RSI، ADX)\n"
            "• تحلیل چندتایم‌فریم ۱H / ۴H / ۱D\n"
            "• ساختار بازار، حجم، الگوهای کندلی\n"
            "• نسبت لانگ/شورت و شاخص ترس و طمع\n"
            "• سناریو A/B و سیگنال لانگ / شورت / صبر با AI\n\n"
            "⚠️ صرفاً آموزشی است؛ توصیه سرمایه‌گذاری قطعی نیست.",
            reply_markup=get_market_keyboard(),
        )
        return
    # هوا
    if text in ("🌤 پیش‌بینی هوا", "پیش‌بینی هوا"):
        track_usage(user_id, "forecast")
        await update.message.reply_text(await weather_forecast(city), reply_markup=get_weather_geo_keyboard()); return
    if text in ("🌫 کیفیت هوا", "کیفیت هوا"):
        track_usage(user_id, "aqi")
        await update.message.reply_text(await air_quality(city), reply_markup=get_weather_geo_keyboard()); return
    if text in ("🗺 فاصله شهرها", "فاصله شهرها", "🗺 فاصله جهانی", "فاصله جهانی"):
        context.user_data["waiting_for"] = "distance"; track_usage(user_id, "distance")
        await update.message.reply_text(
            "🗺 فاصله جهانی\n"
            "🌍 همه شهرها و کشورهای دنیا پشتیبانی می‌شود.\n\n"
            "دو مکان را بفرستید:\n"
            "• تهران مشهد\n"
            "• تهران تا ترکیه\n"
            "• ایران ژاپن\n"
            "• Paris to Tokyo\n"
            "• New York - Brazil",
            reply_markup=get_tools_keyboard(),
        ); return
    if text in ("📍 لوکیشن من", "لوکیشن من"):
        track_usage(user_id, "location")
        await update.message.reply_text(f"📍 لوکیشن را از 📎 بفرستید.\nشهر فعلی: {city}", reply_markup=get_weather_geo_keyboard()); return
    # ابزار
    if text in ("🔢 ماشین‌حساب", "ماشین‌حساب"):
        context.user_data["waiting_for"] = "calc"; track_usage(user_id, "calc")
        await update.message.reply_text("🔢 `2+3*4`", reply_markup=get_tools_keyboard()); return
    if text in ("🔐 پسورد تصادفی", "پسورد تصادفی"):
        track_usage(user_id, "password")
        pwd = generate_password(16)
        await update.message.reply_text(
            "🔐 پسورد تصادفی:\n\n<code>" + pwd + "</code>\n\n👆 روی پسورد بزنید تا کپی شود",
            reply_markup=get_tools_keyboard(),
            parse_mode="HTML",
        ); return
    if text in ("📝 شمارش متن", "شمارش متن"):
        context.user_data["waiting_for"] = "count_text"; track_usage(user_id, "count")
        await update.message.reply_text("📝 متن را بفرستید:", reply_markup=get_tools_keyboard()); return
    # سرگرمی
    if text in ("📖 فال حافظ", "فال حافظ"):
        track_usage(user_id, "hafez"); await update.message.reply_text(await hafez_fal(user_id), reply_markup=get_fun_keyboard()); return
    if text in ("😂 جوک روز", "جوک روز"):
        track_usage(user_id, "joke")
        await update.message.reply_text(
            "😂 دسته جوک را انتخاب کن:\n(بیش از ۸۷۰۰ جوک از farsijokes)",
            reply_markup=get_joke_keyboard(),
        ); return
    # دسته‌های جوک
    _joke_map = {
        "🎲 جوک تصادفی": None,
        "😄 عمومی": "general",
        "🤣 ترکی": "turkish",
        "😂 رشتی": "rashti",
        "😏 قزوینی": "ghazvini",
        "👨 مردان": "men",
        "👩 زنان": "women",
        "🤑 اصفهانی": "isfahani",
        "🔞 سکسی": "adult",
        "🎭 متفرقه": "misc",
        "💀 زشت": "dirty",
    }
    if text in _joke_map:
        track_usage(user_id, "joke")
        cat = _joke_map[text]
        await update.message.reply_text(await joke_of_day(cat, user_id=update.effective_user.id), reply_markup=get_joke_keyboard())
        return
    if text in ("🔙 بازگشت به سرگرمی",):
        await update.message.reply_text("🎮 سرگرمی:", reply_markup=get_fun_keyboard()); return
    if text in ("🧠 دانستنی روز", "دانستنی روز"):
        track_usage(user_id, "fact"); await update.message.reply_text(await fact_of_day(), reply_markup=get_fun_keyboard()); return
    if text in ("💪 چالش امروز", "چالش امروز"):
        track_usage(user_id, "challenge"); await update.message.reply_text(await daily_challenge(), reply_markup=get_fun_keyboard()); return
    if text in ("💖 جمله انگیزشی", "جمله انگیزشی"):
        track_usage(user_id, "motivation"); await update.message.reply_text(f"💖 {get_motivation()}", reply_markup=get_fun_keyboard()); return
    # پروفایل
    if text in ("⚙️ تنظیمات هوشمند", "تنظیمات هوشمند"):
        from bot.database import get_user_preferences
        prefs = get_user_preferences(user_id)
        style_names = {"short": "کوتاه", "balanced": "متعادل", "long": "کامل"}
        await update.message.reply_text(
            "⚙️ تنظیمات هوشمند\n\n"
            f"✍️ سبک پاسخ: {style_names.get(prefs.get('response_style'), 'متعادل')}\n"
            f"💵 ارز پیش‌فرض: {prefs.get('currency', 'USD')}\n\n"
            "این تنظیمات فقط برای شخصی‌سازی تجربه استفاده می‌شوند.",
            reply_markup=get_smart_settings_keyboard(),
        )
        return
    if text in ("✍️ پاسخ کوتاه", "📚 پاسخ کامل", "⚖️ پاسخ متعادل"):
        from bot.database import set_user_preference
        style = "short" if "کوتاه" in text else "long" if "کامل" in text else "balanced"
        set_user_preference(user_id, "response_style", style)
        await update.message.reply_text("✅ سبک پاسخ ذخیره شد.", reply_markup=get_smart_settings_keyboard())
        return
    if text in ("💵 ارز USD", "💶 ارز EUR", "🇮🇷 ارز IRR"):
        from bot.database import set_user_preference
        currency = text.split()[-1]
        set_user_preference(user_id, "currency", currency)
        await update.message.reply_text(f"✅ ارز پیش‌فرض: {currency}", reply_markup=get_smart_settings_keyboard())
        return
    if text == "🔄 بررسی بروزرسانی":
        from bot.handlers.v78_handlers import update_center_command
        await update_center_command(update, context)
        return
    if text == "🧹 پاک‌سازی تنظیمات":
        from bot.database import clear_user_preferences
        clear_user_preferences(user_id)
        await update.message.reply_text("🧹 تنظیمات هوشمند پاک شد.", reply_markup=get_smart_settings_keyboard())
        return
    if text == "🔙 بازگشت به پروفایل":
        await update.message.reply_text("👤 پروفایل:", reply_markup=get_profile_keyboard())
        return
    if text in ("👤 پروفایل من", "پروفایل من"):
        track_usage(user_id, "profile")
        u = update.effective_user
        txt = profile_text(
            user_id, u.first_name or first_name,
            username=u.username, last_name=u.last_name,
            language_code=getattr(u, "language_code", None),
        )
        try:
            photos = await context.bot.get_user_profile_photos(user_id, limit=1)
            if photos.total_count > 0:
                file_id = photos.photos[0][-1].file_id
                await update.message.reply_photo(file_id, caption=txt.replace("**", "").replace("`","")+ "", reply_markup=get_profile_keyboard())
            else:
                await update.message.reply_text(txt.replace("**", "").replace("`",""), reply_markup=get_profile_keyboard())
        except Exception:
            await update.message.reply_text(txt.replace("**", "").replace("`",""), reply_markup=get_profile_keyboard())
        return
    if text in ("📊 آمار من", "آمار من"):
        track_usage(user_id, "stats")
        usage = get_user_usage(user_id) or []
        if usage:
            lines = []
            for row in usage[:15]:
                try:
                    lines.append(f"• {row[0]}: {row[1]}")
                except Exception as _exc:
                    logger.debug("%s: %s", __name__, _exc)
            msg = "📊 آمار:\n" + ("\n".join(lines) if lines else "خالی")
        else:
            msg = "📊 آمار:\nخالی"
        await update.message.reply_text(msg, reply_markup=get_profile_keyboard()); return
    if text in ("🎂 ذخیره تاریخ تولد", "ذخیره تاریخ تولد"):
        context.user_data["waiting_for"] = "birth_save"
        await update.message.reply_text("🎂 `1375/03/15`", reply_markup=get_profile_keyboard()); return
    if text in ("🇮🇷 ایران", "ایران"):
        await update.message.reply_text("🇮🇷 شهر:", reply_markup=get_iran_cities_keyboard()); return
    if text in ("🇮🇶 عراق", "عراق"):
        await update.message.reply_text("🇮🇶 شهر:", reply_markup=get_iraq_cities_keyboard()); return
    if _is_back(text):
        await _send_main(update, context, await build_message(user_id, first_name, city), user_id); return
    if text.startswith("فارسی") or text == "فارسی 🇮🇷":
        update_user_field(user_id, "language", "fa"); await _send_main(update, context, await build_message(user_id, first_name, city), user_id); return
    if text.startswith("English") or text == "English 🇬🇧":
        update_user_field(user_id, "language", "en"); await _send_main(update, context, await build_message(user_id, first_name, city), user_id); return
    if "العربية" in text or "العربيه" in text:
        update_user_field(user_id, "language", "ar"); await _send_main(update, context, await build_message(user_id, first_name, city), user_id); return
    if text in ALL_CITIES:
        update_user_field(user_id, "city", text); update_user_field(user_id, "country", CITY_COUNTRY.get(text, "Iran"))
        await _send_main(update, context, f"✅ شهر → **{text}**\n\n" + await build_message(user_id, first_name, text), user_id); return
