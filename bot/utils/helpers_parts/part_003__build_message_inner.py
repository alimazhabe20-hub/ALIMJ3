# Auto-split part 3: _build_message_inner
async def _build_message_inner(user_id, user_name, city):
    import asyncio

    nl = chr(10)
    city = city or "قم"
    # نام کاربر ممکن است { } داشته باشد و text.format را بشکند
    user_name = str(user_name or "کاربر").replace("{", "(").replace("}", ")")

    try:
        lang = get_user_language(user_id) or "fa"
    except Exception:
        lang = "fa"
    lang = lang if lang in {"fa", "en", "ar"} else "fa"
    weekdays_en = {0:"Saturday",1:"Sunday",2:"Monday",3:"Tuesday",4:"Wednesday",5:"Thursday",6:"Friday"}
    weekdays_ar = {0:"السبت",1:"الأحد",2:"الاثنين",3:"الثلاثاء",4:"الأربعاء",5:"الخميس",6:"الجمعة"}
    months_ar = {1:"يناير",2:"فبراير",3:"مارس",4:"أبريل",5:"مايو",6:"يونيو",7:"يوليو",8:"أغسطس",9:"سبتمبر",10:"أكتوبر",11:"نوفمبر",12:"ديسمبر"}
    hijri_ar = {"محرم":"محرّم","صفر":"صفر","ربیع‌الاول":"ربيع الأول","ربیع الاول":"ربيع الأول","ربیع‌الثانی":"ربيع الآخر","ربیع الثانی":"ربيع الآخر","جمادی‌الاول":"جمادى الأولى","جمادی الاول":"جمادى الأولى","جمادی‌الثانی":"جمادى الآخرة","جمادی الثانی":"جمادى الآخرة","رجب":"رجب","شعبان":"شعبان","رمضان":"رمضان","شوال":"شوال","ذیقعده":"ذو القعدة","ذی الحجه":"ذو الحجة","ذی‌الحجه":"ذو الحجة"}
    section = {
        "prayer": {"fa":f"⏰ **اوقات شرعی امروز ({city}):**","en":f"⏰ **Prayer Times ({city}):**","ar":f"⏰ **أوقات الصلاة اليوم ({city}):**"},
        "weather": {"fa":f"🌦️ **آب و هوای {city}:**","en":f"🌦️ **Weather in {city}:**","ar":f"🌦️ **الطقس في {city}:**"},
        "events_h_today":{"fa":"📌 مناسبت‌های قمری امروز:","en":"📌 Hijri events today:","ar":"📌 المناسبات الهجرية اليوم:"},
        "events_h_tom":{"fa":"📌 مناسبت‌های قمری فردا:","en":"📌 Hijri events tomorrow:","ar":"📌 المناسبات الهجرية غداً:"},
        "events_s_today":{"fa":"📌 مناسبت‌های شمسی امروز:","en":"📌 Solar events today:","ar":"📌 المناسبات الشمسية اليوم:"},
        "events_s_tom":{"fa":"🔮 مناسبت‌های شمسی فردا:","en":"🔮 Solar events tomorrow:","ar":"🔮 المناسبات الشمسية غداً:"},
        "market":{"fa":"📊 قیمت بازار:","en":"📊 Market prices:","ar":"📊 أسعار السوق:"},
    }

    try:
        now = datetime.now(pytz.timezone(config.TIMEZONE))
        country = "Iran"
        try:
            country = get_user_country(user_id) or "Iran"
        except Exception:
            pass
        today = get_today_local(country)
    except Exception:
        now = datetime.now()
        today = jdatetime.date.today()

    try:
        weekday = PERSIAN_WEEKDAYS.get(today.weekday(), "")
        month_name = PERSIAN_MONTHS.get(today.month, "")
        year_p = to_persian_num(today.year)
        month_p = to_persian_num(f"{today.month:02d}")
        day_p = to_persian_num(f"{today.day:02d}")
        greg = today.togregorian()
        if lang == "en":
            persian_date = f"{weekdays_en.get(today.weekday(), greg.strftime('%A'))} {greg.year}/{greg.month:02d}/{greg.day:02d} (Solar: {month_name} {today.day})"
            miladi_date = greg.strftime("%B %d, %A") + f" {greg.year}/{greg.month:02d}/{greg.day:02d}"
        elif lang == "ar":
            persian_date = f"{weekdays_ar.get(today.weekday(), '')} {today.day} {month_name} {today.year}/{today.month:02d}/{today.day:02d}"
            miladi_date = f"{weekdays_ar.get(today.weekday(), greg.strftime('%A'))} {greg.day} {months_ar.get(greg.month, greg.strftime('%B'))} {greg.year}/{greg.month:02d}/{greg.day:02d}"
        else:
            persian_date = f"{weekday} {to_persian_num(today.day)} {month_name} {year_p}/{month_p}/{day_p}"
            miladi_date = greg.strftime("%B %d, %A") + f" {greg.year}/{greg.month:02d}/{greg.day:02d}"
    except Exception:
        persian_date = "—"
        miladi_date = "—"
        greg = datetime.now().date()

    hijri_date = "—"
    hijri_events_text = "• —"
    try:
        hijri = get_hijri_date(greg, country=country) or {}
        hy = to_persian_num(hijri.get("year", 0))
        hm = to_persian_num(f"{int(hijri.get('month', 0) or 0):02d}")
        hd = to_persian_num(f"{int(hijri.get('day', 0) or 0):02d}")
        hname = str(hijri.get("month_name", "—"))
        if lang == "en": hname = {"محرم":"Muharram","صفر":"Safar","ربیع‌الاول":"Rabi al-Awwal","ربیع الاول":"Rabi al-Awwal","ربیع‌الثانی":"Rabi al-Thani","ربیع الثانی":"Rabi al-Thani","جمادی‌الاول":"Jumada al-Awwal","جمادی الاول":"Jumada al-Awwal","جمادی‌الثانی":"Jumada al-Thani","جمادی الثانی":"Jumada al-Thani","رجب":"Rajab","شعبان":"Shaaban","رمضان":"Ramadan","شوال":"Shawwal","ذیقعده":"Dhu al-Qidah","ذی الحجه":"Dhu al-Hijjah","ذی‌الحجه":"Dhu al-Hijjah"}.get(hname,hname)
        elif lang == "ar": hname = hijri_ar.get(hname,hname)
        hijri_date = f"{to_persian_num(hijri.get('day', 0))} {hname} {hy}/{hm}/{hd}"
        hijri_events_list = get_hijri_events(hijri.get("month", 0), hijri.get("day", 0)) or []
        hijri_events_text = chr(10).join([f"• {e}" for e in hijri_events_list]) or "• —"
    except Exception:
        pass

    hijri_tomorrow_text = "• —"
    shamsi_tomorrow_text = "• —"
    shamsi_text = "• —"
    try:
        tomorrow = today + jdatetime.timedelta(days=1)
        hijri_tomorrow = get_hijri_date(tomorrow.togregorian(), country=country) or {}
        hijri_tomorrow_events = get_hijri_events(
            hijri_tomorrow.get("month", 0), hijri_tomorrow.get("day", 0)
        ) or []
        hijri_tomorrow_text = chr(10).join([f"• {e}" for e in hijri_tomorrow_events]) or "• —"
        shamsi_tomorrow = get_shamsi_events(tomorrow.year, tomorrow.month, tomorrow.day) or []
        shamsi_tomorrow_text = chr(10).join([f"• {e}" for e in shamsi_tomorrow]) or "• —"
        shamsi_events_list = get_shamsi_events(today.year, today.month, today.day) or []
        shamsi_text = chr(10).join([f"• {e}" for e in shamsi_events_list]) or "• —"
    except Exception:
        pass

    # درخواست‌های blocking (requests) را در executor اجرا می‌کنیم
    # تا event loop بات هنگام بروزرسانی قفل نشود.
    loop = asyncio.get_running_loop()

    prayer_text = "⚠️ اوقات شرعی در دسترس نیست."
    next_prayer_text = ""
    try:
        prayer_times = await loop.run_in_executor(
            None, lambda: get_prayer_times(city, country=country)
        )
        if prayer_times:
            prayer_names = {"اذان صبح":{"fa":"اذان صبح","en":"Fajr","ar":"الفجر"},"طلوع آفتاب":{"fa":"طلوع آفتاب","en":"Sunrise","ar":"الشروق"},"اذان ظهر":{"fa":"اذان ظهر","en":"Dhuhr","ar":"الظهر"},"اذان عصر":{"fa":"اذان عصر","en":"Asr","ar":"العصر"},"اذان مغرب":{"fa":"اذان مغرب","en":"Maghrib","ar":"المغرب"},"اذان عشاء":{"fa":"اذان عشاء","en":"Isha","ar":"العشاء"}}
            prayer_text = nl.join([f"🕌 {prayer_names.get(k, {}).get(lang, k)}: {v}" for k, v in prayer_times.items()])
            try:
                result = get_next_prayer_time(prayer_times, now)
                if result and result[0]:
                    name, delta = result
                    total_sec = int(getattr(delta, "total_seconds", lambda: delta.seconds)())
                    hours = total_sec // 3600
                    minutes = (total_sec % 3600) // 60
                    seconds = total_sec % 60
                    next_names = {"اذان صبح":{"en":"Fajr","ar":"الفجر"},"طلوع آفتاب":{"en":"Sunrise","ar":"الشروق"},"اذان ظهر":{"en":"Dhuhr","ar":"الظهر"},"اذان عصر":{"en":"Asr","ar":"العصر"},"اذان مغرب":{"en":"Maghrib","ar":"المغرب"},"اذان عشاء":{"en":"Isha","ar":"العشاء"}}
                    pname = next_names.get(name, {}).get(lang, name)
                    if lang == "en":
                        next_prayer_text = nl + f"⏳ Until {pname}: {hours}h {minutes}m {seconds}s" + nl
                    elif lang == "ar":
                        next_prayer_text = nl + f"⏳ حتى {pname}: {hours} ساعة و{minutes} دقيقة و{seconds} ثانية" + nl
                    else:
                        next_prayer_text = nl + f"⏳ تا {pname}: {to_persian_num(hours)} ساعت و {to_persian_num(minutes)} دقیقه و {to_persian_num(seconds)} ثانیه" + nl
            except Exception:
                pass
    except Exception:
        pass

    weather_text = "⚠️ آب و هوا در دسترس نیست."
    try:
        weather = await loop.run_in_executor(None, lambda: get_weather(city))
        if weather:
            weather_text = (
                ((f"🌡️ Temperature: {weather.get('temp', '—')}°C" + nl + f"🌤️ Condition: {weather.get('condition', '—')}" + nl + f"💧 Humidity: {weather.get('humidity', '—')}%") if lang == "en" else (f"🌡️ درجة الحرارة: {weather.get('temp', '—')}°C" + nl + f"🌤️ الحالة: {weather.get('condition', '—')}" + nl + f"💧 الرطوبة: {weather.get('humidity', '—')}%") if lang == "ar" else (f"🌡️ دما: {weather.get('temp', '—')}°C" + nl + f"🌤️ وضعیت: {weather.get('condition', '—')}" + nl + f"💧 رطوبت: {weather.get('humidity', '—')}%"))
            )
    except Exception:
        pass

    market_text = "⚠️ قیمت بازار در دسترس نیست." + nl
    try:
        market = await get_market_prices()
        dollar = market.get("dollar") if isinstance(market, dict) else None
        gold18 = market.get("gold18") if isinstance(market, dict) else None
        parts = []
        if isinstance(dollar, (int, float)):
            parts.append((f"💵 USD: {int(dollar):,} IRR" if lang == "en" else f"💵 الدولار: {int(dollar):,} ريال" if lang == "ar" else f"💵 دلار: {to_persian_num(f'{int(dollar):,}')} ریال"))
        if isinstance(gold18, (int, float)):
            parts.append((f"🥇 18K Gold: {int(gold18):,} IRR" if lang == "en" else f"🥇 الذهب عيار 18: {int(gold18):,} ريال" if lang == "ar" else f"🥇 طلای ۱۸ عیار: {to_persian_num(f'{int(gold18):,}')} ریال"))
        if parts:
            market_text = nl.join(parts) + nl
    except Exception:
        pass

    motivation = "—"
    try:
        motivation_sets = {
            "fa": ["🌄 افق همیشه روشن است، حتی اگر هنوز آن را نبینی. به روشنایی ایمان داشته باش.", "🌅 هر روز فرصتی تازه برای شروع دوباره است. امروز را غنیمت شمار.", "🌟 نور خودت را پیدا کن و بدرخش."],
            "en": ["🌄 The horizon is always bright, even when you cannot see it yet. Keep faith in the light.", "🌅 Every day is a new chance to begin again. Make today count.", "🌟 Find your light and let it shine."],
            "ar": ["🌄 الأفق مشرق دائماً، حتى إن لم تره بعد. ثق بالنور.", "🌅 كل يوم فرصة جديدة للبدء من جديد. اجعل يومك مهماً.", "🌟 ابحث عن نورك ودعه يشرق."]
        }
        motivation = get_motivation(motivation_sets.get(lang)) or "—"
    except Exception:
        pass

    def _safe_text(key, **kwargs):
        try:
            return get_text(user_id, key, **kwargs)
        except Exception:
            return ""

    try:
        message = (
            _safe_text("welcome", name=user_name) + nl + nl
            + (f"📅 امروز (شمسی): {persian_date}" if lang == "fa" else f"📅 Solar date: {persian_date}" if lang == "en" else f"📅 التاريخ الشمسي: {persian_date}") + nl
            + (f"📅 امروز (میلادی): {miladi_date}" if lang == "fa" else f"📅 Gregorian date: {miladi_date}" if lang == "en" else f"📅 التاريخ الميلادي: {miladi_date}") + nl
            + (f"🌙 امروز (قمری): {hijri_date}" if lang == "fa" else f"🌙 Hijri date: {hijri_date}" if lang == "en" else f"🌙 التاريخ الهجري: {hijri_date}") + nl + nl
            + section["events_h_today"][lang] + nl + hijri_events_text + nl + nl
            + section["events_h_tom"][lang] + nl + hijri_tomorrow_text + nl + nl
            + section["events_s_today"][lang] + nl + shamsi_text + nl + nl
            + section["events_s_tom"][lang] + nl + shamsi_tomorrow_text + nl + nl
            + section["prayer"][lang] + nl + prayer_text + next_prayer_text + nl
            + section["weather"][lang] + nl + weather_text + nl + nl
            + section["market"][lang] + nl + market_text + nl
            + ({"fa":"💖 **پیام انگیزشی روز:**","en":"💖 **Daily Motivation:**","ar":"💖 **رسالة تحفيزية اليوم:**"}[lang]) + nl + motivation + nl + nl
            + ({"fa":"🔔 برای تغییر شهر، از دکمه‌های زیر استفاده کن.","en":"🔔 Use the buttons below to change city.","ar":"🔔 استخدم الأزرار أدناه لتغيير المدينة."}[lang])
        )
    except Exception:
        message = (
            f"🌟 سلام {user_name} عزیز!\n\n"
            f"⚠️ بخشی از اطلاعات موقتاً در دسترس نیست. /start را دوباره بفرستید."
        )

    if len(message) > 4000:
        message = message[:3990] + "\n…"
    return message
