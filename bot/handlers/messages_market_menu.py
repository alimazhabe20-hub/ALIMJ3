"""Semantic message-routing handlers. Extracted from the legacy text handler without removing behavior."""
from .messages_common import *  # noqa: F401,F403
from . import messages_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})

async def handle_market_menu(update, context, text, user_id, city=None, first_name=None):
    # تحلیل طلا دقیقاً داخل همان جریان «بازار» و با ساختار منوی تحلیل کریپتو
    # نمایش داده می‌شود؛ وارد بخش/منوی جدید نمی‌شود.
    if text in ("🥇 تحلیل طلا", "تحلیل طلا"):
        try:
            track_usage(user_id, "gold_analysis")
            notice = await update.message.reply_text("⏳ در حال دریافت تحلیل زنده طلا / XAUUSD…")
            report = await analyze_gold("1h")
            chart_note = ""
            try:
                png, chart_note = await get_gold_chart("1h")
            except Exception as chart_exc:
                logger.warning("get_gold_chart failed: %s", chart_exc)
                png, chart_note = None, str(chart_exc)
            try:
                await notice.delete()
            except Exception:
                pass
            # XAUUSD همان منوی Inline تحلیل کریپتو را با نماد gold استفاده می‌کند.
            # بنابراین تایم‌فریم، پرایس‌اکشن، تحلیل هوشمند و بروزرسانی همگی روی همان پیام می‌مانند.
            menu = get_crypto_analysis_keyboard("gold")
            if png:
                from io import BytesIO
                try:
                    bio = BytesIO(png)
                    bio.name = "gold_xauusd_1h.png"
                    chart_msg = await update.message.reply_photo(
                        photo=bio,
                        caption="🥇 <b>تحلیل طلا / XAUUSD — 1H</b>",
                        parse_mode="HTML",
                    )
                    context.user_data["market_chart_message_id"] = chart_msg.message_id
                    context.user_data["market_chart_chat_id"] = update.effective_chat.id
                except Exception as send_exc:
                    logger.warning("gold chart send failed: %s", send_exc)
                    chart_note = chart_note or str(send_exc)
            elif chart_note:
                try:
                    await update.message.reply_text(f"⚠️ نمودار طلا در دسترس نیست: {chart_note[:300]}")
                except Exception:
                    pass
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
            chart_note = ""
            try:
                png, chart_note = await get_gold_chart("1h")
            except Exception as chart_exc:
                logger.warning("get_gold_chart (alias) failed: %s", chart_exc)
                png, chart_note = None, str(chart_exc)
            try:
                await notice.delete()
            except Exception:
                pass
            menu = get_crypto_analysis_keyboard("gold")
            if png:
                from io import BytesIO
                try:
                    bio = BytesIO(png)
                    bio.name = "gold_xauusd_1h.png"
                    chart_msg = await update.message.reply_photo(
                        photo=bio,
                        caption="🥇 Gold / XAUUSD — 1H",
                        parse_mode="HTML",
                    )
                    context.user_data["market_chart_message_id"] = chart_msg.message_id
                    context.user_data["market_chart_chat_id"] = update.effective_chat.id
                except Exception as send_exc:
                    logger.warning("gold chart send (alias) failed: %s", send_exc)
                    chart_note = chart_note or str(send_exc)
            elif chart_note:
                try:
                    await update.message.reply_text(f"⚠️ نمودار طلا در دسترس نیست: {chart_note[:300]}")
                except Exception:
                    pass
            # گزارش کامل را به‌صورت پیام متنی می‌فرستیم تا محدودیت 1024 کاراکتری کپشن باعث ناقص شدن تحلیل نشود.
            chunks = [report[i:i+3900] for i in range(0, len(report or ""), 3900)] or ["داده کافی برای تحلیل طلا در دسترس نیست."]
            text_ids = []
            for i, chunk in enumerate(chunks):
                try:
                    mtxt = await update.message.reply_text(
                        chunk, parse_mode="HTML",
                        reply_markup=menu if i == len(chunks) - 1 else None,
                    )
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
    return False
