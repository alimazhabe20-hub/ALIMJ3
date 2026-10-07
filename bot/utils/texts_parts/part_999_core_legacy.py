from bot.utils.modular_loader import load_modular_part
# دیکشنری کامل متون چندزبانه
TEXTS = {
    "fa": {
        "welcome": "🌟 سلام {name} عزیز! 🌟",
        "prayer": "⏰ **اوقات شرعی امروز ({city}):**",
        "weather": "🌦️ **آب و هوای {city}:**",
        "motivation": "💖 **پیام انگیزشی روز:**",
        "change_city": "🔔 برای تغییر شهر، از دکمه‌های زیر استفاده کن.",
        "city_changed": "✅ شهر شما به **{city}** تغییر کرد.",
        "city_not_found": "❌ شهر '{city}' پیدا نشد.",
        "help": "🤖 **راهنمای ربات:**\n\n"
                "/start - نمایش اطلاعات امروز\n"
                "/city [نام شهر] - تغییر شهر\n"
                "/language - تغییر زبان\n"
                "/calendar - مشاهده تقویم تعاملی\n"
                "/stats - آمار ربات (فقط ادمین)\n"
                "/broadcast [پیام] - ارسال همگانی (فقط ادمین)",
        "language_changed": "✅ زبان شما به **{lang}** تغییر کرد.",
        "no_events": "هیچ مناسبت خاصی ثبت نشده است.",
        "admin_only": "❌ این دستور فقط برای ادمین‌ها قابل استفاده است.",
        "broadcast_sent": "✅ پیام به {count} کاربر ارسال شد.",
        "stats": "📊 **آمار ربات:**\n\n"
                 "👥 تعداد کل کاربران: {total}\n"
                 "📅 کاربران فعال امروز: {active}",
        "calendar_title": "📅 **تقویم {month} {year}**\n\n",
        "calendar_today": "📌 امروز: {date}",
        "calendar_event": "• {event}",
        "not_member": "❌ برای استفاده از این ربات، ابتدا در کانال زیر عضو شوید:\n{channel_link}\n\nپس از عضویت، دوباره `/start` را بفرستید.",
        "next_prayer": "⏳ زمان تا اذان بعدی ({name}): **{hours} ساعت و {minutes} دقیقه**",
        "ai_unavailable": "⚠️ فعلاً سرویس هوش مصنوعی پاسخ نداد. چند ثانیه بعد دوباره امتحان کنید.",
    },
    "en": {
        "welcome": "🌟 Hello dear {name}! 🌟",
        "prayer": "⏰ **Prayer Times ({city}):**",
        "weather": "🌦️ **Weather in {city}:**",
        "motivation": "💖 **Daily Motivation:**",
        "change_city": "🔔 Use the buttons below to change city.",
        "city_changed": "✅ Your city has been changed to **{city}**.",
        "city_not_found": "❌ City '{city}' not found.",
        "help": "🤖 **Bot Commands:**\n\n"
                "/start - Show today's info\n"
                "/city [city name] - Change city\n"
                "/language - Change language\n"
                "/calendar - Interactive calendar\n"
                "/stats - Bot stats (admin only)\n"
                "/broadcast [message] - Broadcast (admin only)",
        "language_changed": "✅ Your language has been changed to **{lang}**.",
        "no_events": "No specific events recorded.",
        "admin_only": "❌ This command is for admins only.",
        "broadcast_sent": "✅ Message sent to {count} users.",
        "stats": "📊 **Bot Stats:**\n\n"
                 "👥 Total users: {total}\n"
                 "📅 Active users today: {active}",
        "calendar_title": "📅 **Calendar {month} {year}**\n\n",
        "calendar_today": "📌 Today: {date}",
        "calendar_event": "• {event}",
        "not_member": "❌ To use this bot, please join the channel below first:\n{channel_link}\n\nAfter joining, send `/start` again.",
        "next_prayer": "⏳ Time until next prayer ({name}): **{hours} hours and {minutes} minutes**",
        "ai_unavailable": "⚠️ The AI service did not respond. Please try again in a few seconds.",
    },
    "ar": {
        "welcome": "🌟 مرحباً عزيزي {name}! 🌟",
        "prayer": "⏰ **أوقات الصلاة اليوم ({city}):**",
        "weather": "🌦️ **الطقس في {city}:**",
        "motivation": "💖 **رسالة تحفيزية اليوم:**",
        "change_city": "🔔 استخدم الأزرار أدناه لتغيير المدينة.",
        "city_changed": "✅ تم تغيير مدينتك إلى **{city}**.",
        "city_not_found": "❌ المدينة '{city}' غير موجودة.",
        "help": "🤖 **تعليمات البوت:**\n\n"
                "/start - عرض معلومات اليوم\n"
                "/city [اسم المدينة] - تغيير المدينة\n"
                "/language - تغيير اللغة\n"
                "/calendar - تقويم تفاعلي\n"
                "/stats - إحصائيات البوت (للمشرفين)\n"
                "/broadcast [رسالة] - إرسال جماعي (للمشرفين)",
        "language_changed": "✅ تم تغيير لغتك إلى **{lang}**.",
        "no_events": "لا توجد مناسبات خاصة مسجلة.",
        "admin_only": "❌ هذا الأمر مخصص للمشرفين فقط.",
        "broadcast_sent": "✅ تم إرسال الرسالة إلى {count} مستخدم.",
        "stats": "📊 **إحصائيات البوت:**\n\n"
                 "👥 إجمالي المستخدمين: {total}\n"
                 "📅 المستخدمين النشطين اليوم: {active}",
        "calendar_title": "📅 **تقويم {month} {year}**\n\n",
        "calendar_today": "📌 اليوم: {date}",
        "calendar_event": "• {event}",
        "not_member": "❌ لاستخدام هذا البوت، يرجى الانضمام إلى القناة أدناه أولاً:\n{channel_link}\n\nبعد الانضمام، أرسل `/start` مرة أخرى.",
        "next_prayer": "⏳ الوقت المتبقي حتى الصلاة القادمة ({name}): **{hours} ساعة و {minutes} دقيقة**",
        "ai_unavailable": "⚠️ لم تستجب خدمة الذكاء الاصطناعي حالياً. حاول مرة أخرى بعد بضع ثوانٍ.",
    }
}

SUPPORTED_LANGUAGES = tuple(TEXTS.keys())
DEFAULT_LANGUAGE = "fa"


load_modular_part(__file__, 'texts_parts/part_001_normalize_language.py')


load_modular_part(__file__, 'texts_parts/part_002_get_text_for_language.py')


load_modular_part(__file__, 'texts_parts/part_003_get_text.py')


# UI labels are translated at render-time so ReplyKeyboard buttons follow the
# user's selected language without duplicating every handler branch.
UI_LABELS = {
    "🏙 انتخاب شهر": {"fa":"🏙 انتخاب شهر","en":"🏙 Choose city","ar":"🏙 اختيار المدينة"},
    "📅 تقویم": {"fa":"📅 تقویم","en":"📅 Calendar","ar":"📅 التقويم"},
    "🌍 زبان": {"fa":"🌍 زبان","en":"🌍 Language","ar":"🌍 اللغة"},
    "➕ بیشتر": {"fa":"➕ بیشتر","en":"➕ More","ar":"➕ المزيد"},
    "🤖 دستیار هوشمند": {"fa":"🤖 دستیار هوشمند","en":"🤖 AI Assistant","ar":"🤖 المساعد الذكي"},
    "🔄 بروزرسانی": {"fa":"🔄 بروزرسانی","en":"🔄 Refresh","ar":"🔄 تحديث"},
    "🎛 انتخاب مدل AI": {"fa":"🎛 انتخاب مدل AI","en":"🎛 Select AI model","ar":"🎛 اختيار نموذج الذكاء الاصطناعي"},
    "🧹 حذف حافظه": {"fa":"🧹 حذف حافظه","en":"🧹 Clear memory","ar":"🧹 مسح الذاكرة"},
    "❌ هیچ سرویسی تنظیم نشده": {"fa":"❌ هیچ سرویسی تنظیم نشده","en":"❌ No service configured","ar":"❌ لا توجد خدمة مُهيأة"},
    "↩️ برگشت": {"fa":"↩️ برگشت","en":"↩️ Back","ar":"↩️ رجوع"},
    "📅 تاریخ و سن": {"fa":"📅 تاریخ و سن","en":"📅 Date & age","ar":"📅 التاريخ والعمر"},
    "🕌 مذهبی": {"fa":"🕌 مذهبی","en":"🕌 Religious","ar":"🕌 ديني"},
    "💰 بازار": {"fa":"💰 بازار","en":"💰 Market","ar":"💰 السوق"},
    "🌤 هوا و مکان": {"fa":"🌤 هوا و مکان","en":"🌤 Weather & location","ar":"🌤 الطقس والموقع"},
    "🛠 ابزارها": {"fa":"🛠 ابزارها","en":"🛠 Tools","ar":"🛠 الأدوات"},
    "🎮 سرگرمی": {"fa":"🎮 سرگرمی","en":"🎮 Fun","ar":"🎮 ترفيه"},
    "🎨 فونت": {"fa":"🎨 فونت","en":"🎨 Fonts","ar":"🎨 الخطوط"},
    "👤 پروفایل": {"fa":"👤 پروفایل","en":"👤 Profile","ar":"👤 الملف الشخصي"},
    "📥 دانلودر فایل": {"fa":"📥 دانلودر فایل","en":"📥 File downloader","ar":"📥 مُنزّل الملفات"},
    "🔄 بررسی بروزرسانی": {"fa":"🔄 بررسی بروزرسانی","en":"🔄 Check for updates","ar":"🔄 التحقق من التحديثات"},
    "🔙 بازگشت": {"fa":"🔙 بازگشت","en":"🔙 Back","ar":"🔙 رجوع"},
    "🔄 مبدل تاریخ": {"fa":"🔄 مبدل تاریخ","en":"🔄 Date converter","ar":"🔄 محوّل التاريخ"},
    "🎂 محاسبه سن": {"fa":"🎂 محاسبه سن","en":"🎂 Age calculator","ar":"🎂 حاسبة العمر"},
    "🎉 روزشمار تولد": {"fa":"🎉 روزشمار تولد","en":"🎉 Birthday countdown","ar":"🎉 العد التنازلي للميلاد"},
    "♈ برج و حیوان": {"fa":"♈ برج و حیوان","en":"♈ Zodiac & animal","ar":"♈ البرج والحيوان"},
    "🌙 سن قمری": {"fa":"🌙 سن قمری","en":"🌙 Lunar age","ar":"🌙 العمر الهجري"},
    "📆 اختلاف تاریخ": {"fa":"📆 اختلاف تاریخ","en":"📆 Date difference","ar":"📆 فرق التاريخ"},
    "👥 اختلاف سن": {"fa":"👥 اختلاف سن","en":"👥 Age difference","ar":"👥 فرق العمر"},
    "📅 تقویم ماه": {"fa":"📅 تقویم ماه","en":"📅 Monthly calendar","ar":"📅 التقويم الشهري"},
    "🔍 مناسبت‌یاب": {"fa":"🔍 مناسبت‌یاب","en":"🔍 Event finder","ar":"🔍 الباحث عن المناسبات"},
    "🌸 شمارش نوروز": {"fa":"🌸 شمارش نوروز","en":"🌸 Nowruz countdown","ar":"🌸 العد التنازلي لنوروز"},
    "🌍 ساعت جهانی": {"fa":"🌍 ساعت جهانی","en":"🌍 World clock","ar":"🌍 الساعة العالمية"},
    "⏳ شمارش‌معکوس": {"fa":"⏳ شمارش‌معکوس","en":"⏳ Countdown","ar":"⏳ العد التنازلي"},
    "🔙 بازگشت به بیشتر": {"fa":"🔙 بازگشت به بیشتر","en":"🔙 Back to More","ar":"🔙 العودة إلى المزيد"},
    "🕋 قبله‌نما": {"fa":"🕋 قبله‌نما","en":"🕋 Qibla","ar":"🕋 القبلة"},
    "📿 اذکار روز": {"fa":"📿 اذکار روز","en":"📿 Daily adhkar","ar":"📿 أذكار اليوم"},
    "📖 آیه و حدیث": {"fa":"📖 آیه و حدیث","en":"📖 Verse & Hadith","ar":"📖 آية وحديث"},
    "🕌 مناسبت مذهبی": {"fa":"🕌 مناسبت مذهبی","en":"🕌 Religious events","ar":"🕌 المناسبات الدينية"},
    "🙏 استخاره": {"fa":"🙏 استخاره","en":"🙏 Istikhara","ar":"🙏 الاستخارة"},
    "🔔 تنظیم اذان": {"fa":"🔔 تنظیم اذان","en":"🔔 Prayer alerts","ar":"🔔 تنبيهات الصلاة"},
    "💵 قیمت کامل بازار": {"fa":"💵 قیمت کامل بازار","en":"💵 Full market prices","ar":"💵 أسعار السوق الكاملة"},
    "💎 ۲۰ ارز برتر کریپتو": {"fa":"💎 ۲۰ ارز برتر کریپتو","en":"💎 Top 20 crypto","ar":"💎 أفضل 20 عملة رقمية"},
    "🔄 تبدیل ارز / کریپتو": {"fa":"🔄 تبدیل ارز / کریپتو","en":"🔄 Currency / crypto converter","ar":"🔄 محوّل العملات / الرقمية"},
    "📈 سود و ضرر": {"fa":"📈 سود و ضرر","en":"📈 Profit & loss","ar":"📈 الربح والخسارة"},
    "🗓 تقویم اقتصادی": {"fa":"🗓 تقویم اقتصادی","en":"🗓 Economic calendar","ar":"🗓 التقويم الاقتصادي"},
    "📊 نمودار و تحلیل ارز دیجیتال": {"fa":"📊 نمودار و تحلیل ارز دیجیتال","en":"📊 Crypto chart & analysis","ar":"📊 مخطط وتحليل العملات الرقمية"},
    "🥇 تحلیل طلا": {"fa":"🥇 تحلیل طلا","en":"🥇 Gold analysis","ar":"🥇 تحليل الذهب"},
    "🟢 🔄 بروزرسانی تحلیل طلا": {"fa":"🟢 🔄 بروزرسانی تحلیل طلا","en":"🟢 🔄 Refresh gold analysis","ar":"🟢 🔄 تحديث تحليل الذهب"},
    "🌤 پیش‌بینی هوا": {"fa":"🌤 پیش‌بینی هوا","en":"🌤 Weather forecast","ar":"🌤 توقعات الطقس"},
    "🌫 کیفیت هوا": {"fa":"🌫 کیفیت هوا","en":"🌫 Air quality","ar":"🌫 جودة الهواء"},
    "📍 لوکیشن من": {"fa":"📍 لوکیشن من","en":"📍 My location","ar":"📍 موقعي"},
    "🔢 ماشین‌حساب": {"fa":"🔢 ماشین‌حساب","en":"🔢 Calculator","ar":"🔢 الآلة الحاسبة"},
    "🔐 پسورد تصادفی": {"fa":"🔐 پسورد تصادفی","en":"🔐 Random password","ar":"🔐 كلمة مرور عشوائية"},
    "📝 شمارش متن": {"fa":"📝 شمارش متن","en":"📝 Text counter","ar":"📝 عدّ النص"},
    "🗺 فاصله جهانی": {"fa":"🗺 فاصله جهانی","en":"🗺 World distance","ar":"🗺 المسافة العالمية"},
    "🔙 بازگشت به مذهبی": {"fa":"🔙 بازگشت به مذهبی","en":"🔙 Back to Religious","ar":"🔙 العودة إلى الديني"},
    "📖 فال حافظ": {"fa":"📖 فال حافظ","en":"📖 Hafez fortune","ar":"📖 فال حافظ"},
    "😂 جوک روز": {"fa":"😂 جوک روز","en":"😂 Joke of the day","ar":"😂 نكتة اليوم"},
    "🧠 دانستنی روز": {"fa":"🧠 دانستنی روز","en":"🧠 Fact of the day","ar":"🧠 معلومة اليوم"},
    "💪 چالش امروز": {"fa":"💪 چالش امروز","en":"💪 Today's challenge","ar":"💪 تحدي اليوم"},
    "💖 جمله انگیزشی": {"fa":"💖 جمله انگیزشی","en":"💖 Motivation","ar":"💖 تحفيز"},
    "🔙 بازگشت به سرگرمی": {"fa":"🔙 بازگشت به سرگرمی","en":"🔙 Back to Fun","ar":"🔙 العودة إلى الترفيه"},
    "⏰ مدیریت یادآوری‌ها": {"fa":"⏰ مدیریت یادآوری‌ها","en":"⏰ Reminder Manager","ar":"⏰ إدارة التذكيرات"},
    "👤 پروفایل من": {"fa":"👤 پروفایل من","en":"👤 My profile","ar":"👤 ملفي الشخصي"},
    "📊 آمار من": {"fa":"📊 آمار من","en":"📊 My stats","ar":"📊 إحصائياتي"},
    "🎂 ذخیره تاریخ تولد": {"fa":"🎂 ذخیره تاریخ تولد","en":"🎂 Save birthday","ar":"🎂 حفظ تاريخ الميلاد"},
    "⚙️ تنظیمات هوشمند": {"fa":"⚙️ تنظیمات هوشمند","en":"⚙️ Smart settings","ar":"⚙️ الإعدادات الذكية"},
    "🔙 بازگشت به پروفایل": {"fa":"🔙 بازگشت به پروفایل","en":"🔙 Back to Profile","ar":"🔙 العودة إلى الملف الشخصي"},
    "✍️ پاسخ کوتاه": {"fa":"✍️ پاسخ کوتاه","en":"✍️ Short answers","ar":"✍️ إجابات قصيرة"},
    "📚 پاسخ کامل": {"fa":"📚 پاسخ کامل","en":"📚 Detailed answers","ar":"📚 إجابات مفصلة"},
    "⚖️ پاسخ متعادل": {"fa":"⚖️ پاسخ متعادل","en":"⚖️ Balanced answers","ar":"⚖️ إجابات متوازنة"},
    "🧹 پاک‌سازی تنظیمات": {"fa":"🧹 پاک‌سازی تنظیمات","en":"🧹 Reset settings","ar":"🧹 إعادة ضبط الإعدادات"},
    "🇮🇷 ایران": {"fa":"🇮🇷 ایران","en":"🇮🇷 Iran","ar":"🇮🇷 إيران"},
    "🇮🇶 عراق": {"fa":"🇮🇶 عراق","en":"🇮🇶 Iraq","ar":"🇮🇶 العراق"},
    "🇬🇧 فونت انگلیسی": {"fa":"🇬🇧 فونت انگلیسی","en":"🇬🇧 English fonts","ar":"🇬🇧 الخطوط الإنجليزية"},
    "🇮🇷 فونت فارسی": {"fa":"🇮🇷 فونت فارسی","en":"🇮🇷 Persian fonts","ar":"🇮🇷 الخطوط الفارسية"},
    "🌈 همه فونت‌ها": {"fa":"🌈 همه فونت‌ها","en":"🌈 All fonts","ar":"🌈 كل الخطوط"},
    "📋 لیست فونت‌ها": {"fa":"📋 لیست فونت‌ها","en":"📋 Font list","ar":"📋 قائمة الخطوط"},
    "🔙 بازگشت فونت": {"fa":"🔙 بازگشت فونت","en":"🔙 Back to fonts","ar":"🔙 العودة إلى الخطوط"},
    "🔔 اعلان‌ها: روشن": {"fa":"🔔 اعلان‌ها: روشن","en":"🔔 Alerts: On","ar":"🔔 التنبيهات: مفعلة"},
    "🔕 اعلان‌ها: خاموش": {"fa":"🔕 اعلان‌ها: خاموش","en":"🔕 Alerts: Off","ar":"🔕 التنبيهات: متوقفة"},
    "🔄 همه روشن": {"fa":"🔄 همه روشن","en":"🔄 Turn all on","ar":"🔄 تشغيل الكل"},
    "⏹ همه خاموش": {"fa":"⏹ همه خاموش","en":"⏹ Turn all off","ar":"⏹ إيقاف الكل"},
    "↩️ برگشت به پروفایل": {"fa":"↩️ برگشت به پروفایل","en":"↩️ Back to Profile","ar":"↩️ العودة إلى الملف الشخصي"},
}


UI_LABELS.update({
    "اذان صبح":{"fa":"اذان صبح","en":"Fajr","ar":"الفجر"},
    "اذان ظهر":{"fa":"اذان ظهر","en":"Dhuhr","ar":"الظهر"},
    "اذان عصر":{"fa":"اذان عصر","en":"Asr","ar":"العصر"},
    "اذان مغرب":{"fa":"اذان مغرب","en":"Maghrib","ar":"المغرب"},
    "اذان عشاء":{"fa":"اذان عشاء","en":"Isha","ar":"العشاء"},
    "پیام بنویسید یا از دکمه‌ها استفاده کنید...":{"fa":"پیام بنویسید یا از دکمه‌ها استفاده کنید...","en":"Type a message or use the buttons...","ar":"اكتب رسالة أو استخدم الأزرار..."},
})


UI_LABELS.update({
    "🎲 جوک تصادفی":{"fa":"🎲 جوک تصادفی","en":"🎲 Random joke","ar":"🎲 نكتة عشوائية"},
    "😄 عمومی":{"fa":"😄 عمومی","en":"😄 General","ar":"😄 عامة"},
    "🤣 ترکی":{"fa":"🤣 ترکی","en":"🤣 Turkish","ar":"🤣 تركية"},
    "😂 رشتی":{"fa":"😂 رشتی","en":"😂 Rashti","ar":"😂 رشتي"},
    "😏 قزوینی":{"fa":"😏 قزوینی","en":"😏 Qazvini","ar":"😏 قزويني"},
    "👨 مردان":{"fa":"👨 مردان","en":"👨 Men","ar":"👨 رجال"},
    "👩 زنان":{"fa":"👩 زنان","en":"👩 Women","ar":"👩 نساء"},
    "🤑 اصفهانی":{"fa":"🤑 اصفهانی","en":"🤑 Isfahani","ar":"🤑 أصفهاني"},
    "🔞 سکسی":{"fa":"🔞 سکسی","en":"🔞 Adult","ar":"🔞 للبالغين"},
    "🎭 متفرقه":{"fa":"🎭 متفرقه","en":"🎭 Miscellaneous","ar":"🎭 متفرقات"},
    "💀 زشت":{"fa":"💀 زشت","en":"💀 Ugly","ar":"💀 قبيحة"},
    "🔙 بازگشت فونت":{"fa":"🔙 بازگشت فونت","en":"🔙 Back to fonts","ar":"🔙 العودة إلى الخطوط"},
    "فارسی 🇮🇷":{"fa":"فارسی 🇮🇷","en":"Persian 🇮🇷","ar":"الفارسية 🇮🇷"},
    "English 🇬🇧":{"fa":"English 🇬🇧","en":"English 🇬🇧","ar":"الإنجليزية 🇬🇧"},
    "العربية 🇸🇦":{"fa":"العربية 🇸🇦","en":"Arabic 🇸🇦","ar":"العربية 🇸🇦"},
})

from contextvars import ContextVar
_CURRENT_LANGUAGE = ContextVar("alimj3_current_language", default="fa")

load_modular_part(__file__, 'texts_parts/part_004_set_current_language.py')

load_modular_part(__file__, 'texts_parts/part_005_current_language.py')

load_modular_part(__file__, 'texts_parts/part_006_ui.py')

load_modular_part(__file__, 'texts_parts/part_007_canonical_ui_text.py')
