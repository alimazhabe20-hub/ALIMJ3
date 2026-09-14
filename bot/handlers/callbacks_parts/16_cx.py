async def _handle_cx(query, update, context, data, user_id):
    """Extracted callback branch; preserves original behavior."""
    parts = data.split(":")
    if len(parts) < 3:
        await _safe_answer(query)
        return
    action, symbol = parts[1], parts[2]
    context.user_data["crypto_symbol"] = symbol
    _loading_labels = {
        "ai": "🧠 در حال تحلیل هوشمند…",
        "ict": "📐 در حال تحلیل ICT…",
        "pa": "🧠 در حال تحلیل پرایس‌اکشن…",
        "day": "📅 در حال آماده‌سازی تحلیل روزانه…",
        "hr": "⏰ در حال آماده‌سازی تحلیل ساعتی…",
        "4h": "🕓 در حال آماده‌سازی تحلیل 4 ساعته…",
        "15m": "🕒 در حال آماده‌سازی تحلیل 15 دقیقه‌ای…",
        "rec": "🎯 در حال تهیه توصیه معاملاتی…",
        "der": "📡 در حال اسکن مشتقات…",
        "risk": "🎲 در حال محاسبه ریسک…",
        "scan": "🔍 در حال اسکن بازار…",
        "ref": "🔄 در حال بروزرسانی…",
        "gold": "🥇 در حال تحلیل طلا…",
        "pos": "📐 آماده‌سازی سایز پوزیشن…",
        "al": "🔔 آماده‌سازی هشدار…",
    }
    await _safe_answer(query, _loading_labels.get(action, "⏳ در حال پردازش…"))
    try:
        from bot.logger import logger
        from bot.features.market.finance import (
            analyze_crypto, analyze_gold, get_crypto_chart, get_gold_chart, get_crypto_analysis_keyboard,
            trading_recommendation, derivatives_radar, risk_scenarios,
            position_size_guide, entry_alert_text, market_scanner,
        )
        from bot.features.market.finance_ict import analyze_ict
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
            """Split Telegram text safely without dropping or duplicating content.

            Prefer paragraph/line/word boundaries.  A hard split is only used as
            the final fallback; the original text is preserved byte-for-byte
            apart from trimming the outer whitespace once.  HTML tags are not
            stripped here because doing so can silently remove visible content
            from AI reports.
            """
            raw = (txt or "").strip()
            if not raw:
                return []

            chunks = []
            current = ""

            def _flush():
                nonlocal current
                if current:
                    chunks.append(current)
                    current = ""

            for line in raw.splitlines():
                candidate = line if not current else current + "\n" + line
                if len(candidate) <= limit:
                    current = candidate
                    continue

                _flush()
                remaining = line
                while len(remaining) > limit:
                    cut = remaining.rfind(" ", 0, limit + 1)
                    if cut < max(1, limit // 2):
                        cut = limit
                    chunks.append(remaining[:cut].rstrip())
                    remaining = remaining[cut:].lstrip()
                current = remaining

            _flush()
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
            """Update a long analysis in-place, reusing message IDs whenever possible."""
            import asyncio

            lock = context.user_data.get("_market_analysis_update_lock")
            if lock is None:
                lock = asyncio.Lock()
                context.user_data["_market_analysis_update_lock"] = lock

            async with lock:
                old_ids = list(context.user_data.get("market_analysis_text_ids") or [])
                chat_id = context.user_data.get("market_analysis_chat_id") or query.message.chat_id
                chunks = _split_telegram_text(full_text, limit=3900) or ["داده کافی نیست."]
                bot = context.bot
                ids = []

                # Reuse existing messages first. This prevents long ICT/Smart
                # analyses from deleting and recreating chunks on every update.
                for index, chunk in enumerate(chunks):
                    old_id = old_ids[index] if index < len(old_ids) else None
                    if old_id is not None:
                        try:
                            await bot.edit_message_text(
                                chat_id=chat_id, message_id=old_id, text=chunk,
                                parse_mode="HTML", reply_markup=None
                            )
                            ids.append(old_id)
                            continue
                        except Exception:
                            pass
                    try:
                        m = await bot.send_message(chat_id=chat_id, text=chunk, parse_mode="HTML")
                        ids.append(m.message_id)
                    except Exception:
                        # Retry as plain text only for malformed AI HTML; never
                        # truncate a chunk, otherwise the analysis can lose data.
                        plain = re.sub(r"<[^>]*>", "", chunk)
                        m = await bot.send_message(chat_id=chat_id, text=plain)
                        ids.append(m.message_id)

                # Delete only surplus old chunks.
                for old_id in old_ids[len(chunks):]:
                    try:
                        await bot.delete_message(chat_id=chat_id, message_id=old_id)
                    except Exception:
                        pass

                # Keyboard belongs only to the final text chunk.
                for msg_id in ids[:-1]:
                    try:
                        await bot.edit_message_reply_markup(
                            chat_id=chat_id, message_id=msg_id, reply_markup=None
                        )
                    except Exception:
                        pass
                try:
                    await bot.edit_message_reply_markup(
                        chat_id=chat_id, message_id=ids[-1], reply_markup=menu
                    )
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
                    logger.warning("market analysis text update failed: %s", _txt_exc)
                    try:
                        await _send_full_text(full_input, reply_to=query.message, reply_markup=menu)
                    except Exception as _fb:
                        logger.warning("market analysis fallback send failed: %s", _fb)
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

        if action == "ict":
            # تحلیل ICT به‌صورت مستقیم از همان منوی تحلیل کریپتو اجرا می‌شود؛
            # دکمه دقیقاً زیر «تحلیل هوشمند حرفه‌ای» قرار دارد.
            ict_timeframe = context.user_data.get("crypto_ai_timeframe", "1h")
            if ict_timeframe not in ("15m", "1h", "4h", "1d"):
                ict_timeframe = "1h"
            try:
                ict_report = await analyze_ict(symbol, interval=ict_timeframe)
            except Exception as exc:
                logger.exception("ICT callback analysis failed for %s/%s: %s", symbol, ict_timeframe, exc)
                ict_report = "❌ تحلیل ICT فعلاً در دسترس نیست؛ دوباره تلاش کنید."
            safe_ict = html.escape((ict_report or "داده کافی برای تحلیل ICT وجود ندارد.").strip())
            out = (
                f"📐 <b>تحلیل ICT — {html.escape(symbol.upper())} / {ict_timeframe.upper()}</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                + safe_ict
            )
            await _edit_text(out)
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
            # گزارش کامل ۱۶ بخشی با تشخیص ناقص بودن و ادامه خودکار (crypto_ai_report)
            ai_timeframe = context.user_data.get("crypto_ai_timeframe", "4h")
            if ai_timeframe not in ("15m", "1h", "4h", "1d"):
                ai_timeframe = "4h"
            try:
                base = await analyze_crypto(symbol, timeframe=ai_timeframe)
                from bot.services.crypto_ai_report import build_crypto_ai_report
                answer = await build_crypto_ai_report(
                    user_id=query.from_user.id,
                    symbol=symbol,
                    base_report=base or "",
                    timeframe=ai_timeframe.upper(),
                )
            except Exception as exc:
                logger.exception("smart AI analysis failed for %s/%s: %s", symbol, ai_timeframe, exc)
                answer = f"❌ تحلیل هوشمند فعلاً در دسترس نیست.\n{html.escape(str(exc)[:200])}"
            safe_answer = html.escape((answer or "داده کافی برای تحلیل هوشمند وجود ندارد.").strip())
            out = "🧠 <b>تحلیل هوشمند حرفه‌ای</b>\n━━━━━━━━━━━━━━━━━━━━\n" + safe_answer
            chart_days = {"15m": 3, "1h": 7, "4h": 30, "1d": 90}.get(ai_timeframe, 30)
            try:
                png, _cap = await get_crypto_chart(symbol, chart_days)
            except Exception:
                png = None
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
            context.user_data["crypto_ai_timeframe"] = "15m"
            if symbol.lower() in ("gold", "xau", "xauusd", "xau/usd"):
                txt = await analyze_gold("15m")
                png, _ = await get_gold_chart("15m")
                await _edit_photo_caption(png, "🥇 <b>تحلیل طلا / XAUUSD — 15M</b>\n━━━━━━━━━━━━━━━━━━━━\n" + (txt or "داده کافی نیست."))
            else:
                txt = await analyze_crypto(symbol, timeframe="15m")
                png, _ = await get_crypto_chart(symbol, 3)
                await _edit_photo_caption(png, "🧠 <b>تحلیل کریپتو — 15M</b>\n━━━━━━━━━━━━━━━━━━━━\n" + (txt or "داده کافی نیست."))
            return

        if action == "day":
            context.user_data["crypto_ai_timeframe"] = "1d"
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
            context.user_data["crypto_ai_timeframe"] = "1h"
            if symbol.lower() in ("gold", "xau", "xauusd", "xau/usd"):
                base = await analyze_gold("1h")
                png, _ = await get_gold_chart("1h")
                await _edit_photo_caption(png, "🥇 <b>تحلیل طلا / XAUUSD — 1H</b>\n━━━━━━━━━━━━━━━━━━━━\n" + (base or "داده کافی نیست."))
                return
            base = await analyze_crypto(symbol, timeframe="1h")
            report = base
            png, _cap = await get_crypto_chart(symbol, 7)
            await _edit_photo_caption(png, report or "داده کافی نیست.")

        elif action == "4h":
            context.user_data["crypto_ai_timeframe"] = "4h"
            if symbol.lower() in ("gold", "xau", "xauusd", "xau/usd"):
                txt = await analyze_gold("4h")
                png, _ = await get_gold_chart("4h")
                await _edit_photo_caption(png, "🥇 <b>تحلیل طلا / XAUUSD — 4H</b>\n━━━━━━━━━━━━━━━━━━━━\n" + (txt or "داده کافی نیست."))
            else:
                txt = await analyze_crypto(symbol, timeframe="4h")
                png, _ = await get_crypto_chart(symbol, 30)
                await _edit_photo_caption(png, "🧠 <b>تحلیل کریپتو — 4H</b>\n━━━━━━━━━━━━━━━━━━━━\n" + (txt or "داده کافی نیست."))
            return

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
