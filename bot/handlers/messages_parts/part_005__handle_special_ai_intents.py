async def _handle_special_ai_intents(update, context, user_id, text: str) -> bool:
    """نمودار، جستجو، یادآوری، موسیقی — True اگر کامل هندل شد."""
    import re
    from io import BytesIO
    from bot.database import add_reminder
    # یادآوری
    rem = parse_natural_reminder(text)
    if rem:
        body, when, repeat_type, repeat_every = rem
        add_reminder(
            user_id,
            body,
            when.isoformat(),
            repeat_type=repeat_type,
            repeat_every=repeat_every,
        )
        repeat_label = {
            "daily": "روزانه",
            "weekly": "هفتگی",
            "monthly": "ماهانه",
            "every_minutes": f"هر {repeat_every} دقیقه",
            "every_hours": f"هر {repeat_every} ساعت",
        }.get(repeat_type, "یک‌بار")
        await update.message.reply_text(
            f"⏰ یادآوری ثبت شد.\nموضوع: {body}\nزمان: {when.strftime('%Y-%m-%d %H:%M')}\nتکرار: {repeat_label}",
        )
        return True
    # درخواست لینک را قبل از AI عمومی هندل کن تا پاسخ‌هایی مثل «دسترسی مستقیم ندارم» تولید نشود.
    link_query = _extract_link_search_query(text, get_last_answer(user_id))
    if link_query:
        notice = await update.message.reply_text("🔎 در حال پیدا کردن لینک...")
        try:
            result = await web_search(link_query, max_results=5)
            await update.message.reply_text(result)
        finally:
            try:
                await notice.delete()
            except Exception as _exc:
                logger.debug("link-search notice delete failed: %s", _exc)
        return True
    # Weather/Crypto عمدی اینجا مستقیم پاسخ داده نمی‌شوند.
    # V41.1: اجازه بده Capability Router + Function Calling ابزار واقعی را اجرا کند
    # و خود AI نتیجه را به زبان طبیعی برای کاربر بنویسد؛ خروجی خام ابزار کپی نشود.
    # جستجوی فروشگاهی مستقیم: لینک واقعی را از ماژول خرید می‌گیریم، نه پاسخ حدسی AI.
    if classify_intent(text) == "product_search" and not classify_intent(text) == "crypto_price":
        q = re.sub(r"(?:لینک|خرید|قیمت|فروشگاه|محصول|buy|price|shop|link)", " ", text, flags=re.I).strip(" :،,")
        if len(q) >= 2:
            notice = await update.message.reply_text("🔎 در حال پیدا کردن فروشگاه‌ها و لینک‌های واقعی...")
            try:
                from bot.features.market.shopping import search_shopping
                result = await search_shopping(q, max_results=8, user_id=user_id)
                await update.message.reply_text(result)
            except Exception:
                logger.exception("product search failed for user=%s", user_id)
                await update.message.reply_text("⚠️ جستجوی خرید فعلاً در دسترس نیست. چند ثانیه بعد دوباره امتحان کنید.")
            finally:
                try: await notice.delete()
                except Exception: pass
            return True
    # Market Intelligence: تحلیل چندتایم‌فریمی با داده زنده، فقط وقتی درخواست تحلیل روشن است.
    market_match = re.search(r"(?:تحلیل|آنالیز|analyze|analysis)\s+(?:ارز|رمزارز|crypto)?\s*([A-Za-z]{2,12}|بیت\s*کوین|اتریوم|تتر|سولانا|ریپل|دوج\s*کوین|بایننس|کاردانو)\b", text, re.I)
    if market_match:
        symbol = re.sub(r"\s+", "", market_match.group(1).lower())
        symbol = {"بیتکوین":"btc","بیت کوین":"btc","اتریوم":"eth","تتر":"usdt","سولانا":"sol","ریپل":"xrp","دوجکوین":"doge","بایننس":"bnb","کاردانو":"ada"}.get(symbol, symbol)
        # جلوگیری از تداخل با کلمات عمومی انگلیسی
        if symbol not in {"this", "that", "with", "from", "for", "the", "your"}:
            notice = await update.message.reply_text("📊 در حال تحلیل چندتایم‌فریمی با داده زنده…")
            try:
                from bot.services.v72_platform import market_intelligence, market_summary
                data = await market_intelligence(symbol)
                await update.message.reply_text(market_summary(data))
            except Exception:
                logger.exception("market intelligence failed for user=%s", user_id)
                await update.message.reply_text("⚠️ تحلیل بازار فعلاً در دسترس نیست. چند لحظه بعد دوباره امتحان کنید.")
            finally:
                try: await notice.delete()
                except Exception: pass
            return True
    # جستجوی وب
    m = re.match(r"^(جستجو|سرچ|search)\s*[:：]?\s*(.+)$", text, re.I | re.S)
    if m or re.search(r"\b(در\s*اینترنت|تو\s*وب)\s*جستجو", text, re.I):
        q = m.group(2).strip() if m else re.sub(r".*جستجو\s*[:：]?", "", text, flags=re.I).strip()
        notice = await update.message.reply_text("🔎 در حال جستجو...")
        try:
            try:
                from bot.services.v72_platform import web_intelligence_search
                intel = await web_intelligence_search(q, max_results=5)
                sources = intel.get("sources") or []
                if sources:
                    lines = [f"🔎 نتایج هوشمند برای «{q}»:"]
                    for src in sources:
                        title = (src.get("title") or src.get("domain") or "منبع")[:160]
                        lines.append(f"• {title}\n  {src.get('url','')}")
                    result = "\n\n".join(lines)
                else:
                    result = intel.get("raw") or "نتیجه‌ای پیدا نشد."
            except Exception:
                logger.exception("web intelligence failed for user=%s", user_id)
                result = await web_search(q)
            await update.message.reply_text(result[:4000])
        finally:
            try:
                await notice.delete()
            except Exception as _exc:
                logger.debug("%s: %s", __name__, _exc)
        return True
    # نمودار
    chart = parse_chart_request(text)
    if chart:
        title, labels, values, ctype = chart
        notice = await update.message.reply_text("📊 در حال رسم نمودار...")
        try:
            png = make_chart_image(title, labels, values, ctype)
            bio = BytesIO(png)
            bio.name = "chart.png"
            await update.message.reply_photo(photo=bio, caption=title)
        except Exception:
            logger.exception("chart generation failed for user=%s", user_id)
            await update.message.reply_text("⚠️ ساخت نمودار ناموفق بود. لطفاً دوباره تلاش کنید.")
        finally:
            try:
                await notice.delete()
            except Exception as _exc:
                logger.debug("%s: %s", __name__, _exc)
        return True
    # موسیقی
    if re.search(r"(موسیقی|آهنگ|music)\s*بساز|(بساز|تولید)\s*(موسیقی|آهنگ|افکت)", text, re.I):
        notice = await update.message.reply_text("🎵 در حال ساخت موسیقی...")
        try:
            audio = await generate_music(text)
            bio = BytesIO(audio)
            bio.name = "music.mp3"
            await update.message.reply_audio(audio=bio, caption="🎵")
        except Exception:
            logger.exception("music generation failed for user=%s", user_id)
            await update.message.reply_text("⚠️ ساخت موسیقی فعلاً در دسترس نیست. لطفاً بعداً دوباره تلاش کنید.")
        finally:
            try:
                await notice.delete()
            except Exception as _exc:
                logger.debug("%s: %s", __name__, _exc)
        return True
    return False
