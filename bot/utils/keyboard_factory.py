from bot.utils.city_data import IRAN_CITIES, IRAQ_CITIES
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from bot.utils.texts import ui

def get_refresh_button():
    """فقط دکمه بروزرسانی زیر پیام"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(ui("🔄 بروزرسانی"), callback_data="refresh_main")]
    ])

def get_main_keyboard(user_id=None):
    """کیبورد اصلی؛ در صورت وجود کاربر، بخش‌های پرتکرار را بالاتر می‌آورد."""
    rows = [
        [KeyboardButton(ui("🏙 انتخاب شهر")), KeyboardButton(ui("📅 تقویم"))],
        [KeyboardButton(ui("🌍 زبان")), KeyboardButton(ui("➕ بیشتر"))],
        [KeyboardButton(ui("🤖 دستیار هوشمند"))],
    ]
    # Personalization is intentionally conservative: only reorder existing buttons.
    if user_id is not None:
        try:
            from bot.database import get_top_user_features
            top = {name for name, _count in get_top_user_features(user_id, 3)}
            priority = []
            if "market" in top or "crypto_top" in top or "crypto_full" in top:
                priority.append(rows[1])
            if "forecast" in top or "aqi" in top or "location" in top:
                priority.append(rows[0])
            if priority:
                seen = {id(r) for r in priority}
                rows = priority + [r for r in rows if id(r) not in seen]
        except Exception:
            pass
    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder=ui("پیام بنویسید یا از دکمه‌ها استفاده کنید..."),
    )

def get_ai_keyboard(user_id=None):
    """دکمه‌های شیشه‌ای زیر پیام AI: انتخاب ارائه‌دهنده و پاک‌کردن حافظه."""
    from bot.services.ai_service import get_selected_model, _PROVIDER_PRETTY
    selected = get_selected_model(user_id) if user_id is not None else None
    selected_text = "🎛 انتخاب مدل AI"
    if selected:
        provider = selected[0]
        pretty = _PROVIDER_PRETTY.get(provider, provider)
        selected_text = f"🎛 فعال: {pretty}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(selected_text, callback_data="ai_models")],
        [InlineKeyboardButton(ui("🧹 حذف حافظه"), callback_data="ai_clear_memory")],
    ])

def get_ai_model_keyboard(user_id=None):
    """
    لیست ارائه‌دهنده‌ها (نه تک‌تک مدل‌ها).
    با انتخاب یک ارائه‌دهنده، همه مدل‌هایش به‌صورت خودکار امتحان می‌شوند.
    """
    from bot.services.ai_service import available_providers, get_selected_model
    selected = get_selected_model(user_id) if user_id is not None else None
    selected_provider = selected[0] if selected else None
    rows = []
    for index, (provider, label) in enumerate(available_providers()):
        mark = "✅ " if selected_provider == provider else ""
        rows.append([
            InlineKeyboardButton(
                f"{mark}{label}",
                callback_data=f"ai_provider:{index}",
            )
        ])
    if not rows:
        rows.append([InlineKeyboardButton(ui("❌ هیچ سرویسی تنظیم نشده"), callback_data="ai_noop")])
    rows.append([InlineKeyboardButton(ui("↩️ برگشت"), callback_data="ai_models_back")])
    return InlineKeyboardMarkup(rows)

def get_more_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(ui("📅 تاریخ و سن")), KeyboardButton(ui("🕌 مذهبی"))],
            [KeyboardButton(ui("💰 بازار")), KeyboardButton(ui("🌤 هوا و مکان"))],
            [KeyboardButton(ui("🛠 ابزارها")), KeyboardButton(ui("🎮 سرگرمی"))],
            [KeyboardButton(ui("🎨 فونت")), KeyboardButton(ui("👤 پروفایل"))],
            [KeyboardButton(ui("📥 دانلودر فایل"))],
            [KeyboardButton(ui("🔄 بررسی بروزرسانی"))],
            [KeyboardButton(ui("🔙 بازگشت"))],
        ],
        resize_keyboard=True,
    )

def get_date_tools_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(ui("🔄 مبدل تاریخ")), KeyboardButton(ui("🎂 محاسبه سن"))],
            [KeyboardButton(ui("🎉 روزشمار تولد")), KeyboardButton(ui("♈ برج و حیوان"))],
            [KeyboardButton(ui("🌙 سن قمری")), KeyboardButton(ui("📆 اختلاف تاریخ"))],
            [KeyboardButton(ui("👥 اختلاف سن")), KeyboardButton(ui("📅 تقویم ماه"))],
            [KeyboardButton(ui("🔍 مناسبت‌یاب")), KeyboardButton(ui("🌸 شمارش نوروز"))],
            [KeyboardButton(ui("🌍 ساعت جهانی")), KeyboardButton(ui("⏳ شمارش‌معکوس"))],
            [KeyboardButton(ui("🔙 بازگشت به بیشتر"))],
        ],
        resize_keyboard=True,
    )

def get_religious_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(ui("🕋 قبله‌نما")), KeyboardButton(ui("📿 اذکار روز"))],
            [KeyboardButton(ui("📖 آیه و حدیث")), KeyboardButton(ui("🕌 مناسبت مذهبی"))],
            [KeyboardButton(ui("🙏 استخاره")), KeyboardButton(ui("🔔 تنظیم اذان"))],
            [KeyboardButton(ui("🔙 بازگشت به بیشتر"))],
        ],
        resize_keyboard=True,
    )

def get_market_keyboard():
    """منوی بازار با دکمه‌های واضح و نشانه‌های رنگی برای تشخیص سریع بخش‌ها."""
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(ui("💵 قیمت کامل بازار")), KeyboardButton(ui("💎 ۲۰ ارز برتر کریپتو"))],
            [KeyboardButton(ui("🔄 تبدیل ارز / کریپتو")), KeyboardButton(ui("📈 سود و ضرر"))],
            [KeyboardButton(ui("🗓 تقویم اقتصادی"))],
            [KeyboardButton(ui("📊 نمودار و تحلیل ارز دیجیتال"))],
            [KeyboardButton(ui("🥇 تحلیل طلا"))],
            [KeyboardButton(ui("🔙 بازگشت به بیشتر"))],
        ],
        resize_keyboard=True,
    )


def get_gold_analysis_keyboard():
    """کیبورد اختصاصی تحلیل طلا؛ طلا بعد از گزارش کریپتو به‌صورت مستقل نمایش داده می‌شود."""
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(ui("🟢 🔄 بروزرسانی تحلیل طلا"))],
            [KeyboardButton(ui("📊 نمودار و تحلیل ارز دیجیتال"))],
        ],
        resize_keyboard=True,
    )

def get_weather_geo_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(ui("🌤 پیش‌بینی هوا")), KeyboardButton(ui("🌫 کیفیت هوا"))],
            [KeyboardButton(ui("📍 لوکیشن من"))],
            [KeyboardButton(ui("🔙 بازگشت به بیشتر"))],
        ],
        resize_keyboard=True,
    )

def get_tools_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(ui("🔢 ماشین‌حساب")), KeyboardButton(ui("🔐 پسورد تصادفی"))],
            [KeyboardButton(ui("📝 شمارش متن")), KeyboardButton(ui("🗺 فاصله جهانی"))],
            [KeyboardButton(ui("🔙 بازگشت به بیشتر"))],
        ],
        resize_keyboard=True,
    )

def get_azan_keyboard(settings: dict = None):
    """کیبورد تنظیم اذان با وضعیت فعلی هر نماز."""
    if not settings:
        settings = {
            "enabled": True,
            "fajr": True, "dhuhr": False, "asr": False,
            "maghrib": True, "isha": False,
        }

    def mark(on: bool) -> str:
        return "✅" if on else "❌"

    master = ui("🔔 اعلان‌ها: روشن") if settings.get("enabled") else ui("🔕 اعلان‌ها: خاموش")
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(master)],
            [
                KeyboardButton(f"{mark(settings.get('fajr'))} {ui('اذان صبح')}"),
                KeyboardButton(f"{mark(settings.get('dhuhr'))} {ui('اذان ظهر')}"),
            ],
            [
                KeyboardButton(f"{mark(settings.get('asr'))} {ui('اذان عصر')}"),
                KeyboardButton(f"{mark(settings.get('maghrib'))} {ui('اذان مغرب')}"),
            ],
            [
                KeyboardButton(f"{mark(settings.get('isha'))} {ui('اذان عشاء')}"),
            ],
            [KeyboardButton(ui("🔄 همه روشن")), KeyboardButton(ui("⏹ همه خاموش"))],
            [KeyboardButton(ui("🔙 بازگشت به مذهبی"))],
        ],
        resize_keyboard=True,
    )

def get_fun_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(ui("📖 فال حافظ")), KeyboardButton(ui("😂 جوک روز"))],
            [KeyboardButton(ui("🧠 دانستنی روز")), KeyboardButton(ui("💪 چالش امروز"))],
            [KeyboardButton(ui("💖 جمله انگیزشی"))],
            [KeyboardButton(ui("🔙 بازگشت به بیشتر"))],
        ],
        resize_keyboard=True,
    )

def get_joke_keyboard():
    """کیبورد دسته‌بندی جوک"""
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(ui("🎲 جوک تصادفی")), KeyboardButton(ui("😄 عمومی"))],
            [KeyboardButton(ui("🤣 ترکی")), KeyboardButton(ui("😂 رشتی"))],
            [KeyboardButton(ui("😏 قزوینی")), KeyboardButton(ui("👨 مردان"))],
            [KeyboardButton(ui("👩 زنان")), KeyboardButton(ui("🤑 اصفهانی"))],
            [KeyboardButton(ui("🔞 سکسی")), KeyboardButton(ui("🎭 متفرقه"))],
            [KeyboardButton(ui("💀 زشت"))],
            [KeyboardButton(ui("🔙 بازگشت به سرگرمی"))],
        ],
        resize_keyboard=True,
    )

def get_profile_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(ui("👤 پروفایل من")), KeyboardButton(ui("📊 آمار من"))],
            [KeyboardButton(ui("🎂 ذخیره تاریخ تولد")), KeyboardButton(ui("⚙️ تنظیمات هوشمند"))],
            [KeyboardButton(ui("🔄 بررسی بروزرسانی"))],
            [KeyboardButton(ui("🔙 بازگشت به بیشتر"))],
        ],
        resize_keyboard=True,
    )

def get_smart_settings_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(ui("✍️ پاسخ کوتاه")), KeyboardButton(ui("📚 پاسخ کامل"))],
            [KeyboardButton(ui("⚖️ پاسخ متعادل")), KeyboardButton(ui("💵 ارز USD"))],
            [KeyboardButton(ui("💶 ارز EUR")), KeyboardButton(ui("🇮🇷 ارز IRR"))],
            [KeyboardButton(ui("🧹 پاک‌سازی تنظیمات"))],
            [KeyboardButton(ui("🔙 بازگشت به پروفایل"))],
        ], resize_keyboard=True
    )

def get_country_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(ui("🇮🇷 ایران")), KeyboardButton(ui("🇮🇶 عراق"))],
            [KeyboardButton(ui("🔙 بازگشت"))],
        ],
        resize_keyboard=True,
    )

def get_iran_cities_keyboard():
    buttons = []
    row = []
    for city in IRAN_CITIES:
        row.append(KeyboardButton(city))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([KeyboardButton(ui("🔙 بازگشت"))])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def get_iraq_cities_keyboard():
    buttons = []
    row = []
    for city in IRAQ_CITIES:
        row.append(KeyboardButton(city))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([KeyboardButton(ui("🔙 بازگشت"))])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def get_language_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(ui("فارسی 🇮🇷")), KeyboardButton(ui("English 🇬🇧")), KeyboardButton(ui("العربية 🇸🇦"))],
            [KeyboardButton(ui("🔙 بازگشت"))],
        ],
        resize_keyboard=True,
    )

def get_font_keyboard():
    """کیبورد فونت: فارسی / انگلیسی / همه"""
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(ui("🇬🇧 فونت انگلیسی")), KeyboardButton(ui("🇮🇷 فونت فارسی"))],
            [KeyboardButton(ui("🌈 همه فونت‌ها")), KeyboardButton(ui("📋 لیست فونت‌ها"))],
            [KeyboardButton(ui("🔙 بازگشت به بیشتر"))],
        ],
        resize_keyboard=True,
    )

def get_font_en_keyboard():
    from bot.features.fonts.converter import EN_STYLES
    from bot.features.fonts.styles import FONT_NAMES
    buttons, row = [], []
    for k in EN_STYLES:
        label = FONT_NAMES.get(k, k)[:18]
        row.append(KeyboardButton(label))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([KeyboardButton(ui("🔙 بازگشت فونت"))])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def get_font_fa_keyboard():
    from bot.features.fonts.converter import FA_STYLES
    from bot.features.fonts.styles import FONT_NAMES
    buttons, row = [], []
    for k in FA_STYLES:
        label = FONT_NAMES.get(k, k)[:18]
        row.append(KeyboardButton(label))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([KeyboardButton(ui("🔙 بازگشت فونت"))])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# Canonical registry used by startup checks and future feature modules.
# Values are callables; existing imports/functions remain unchanged.
KEYBOARD_BUILDERS = (
    get_refresh_button, get_main_keyboard, get_ai_keyboard, get_ai_model_keyboard,
    get_more_keyboard, get_date_tools_keyboard, get_religious_keyboard, get_market_keyboard,
    get_weather_geo_keyboard, get_tools_keyboard, get_azan_keyboard, get_fun_keyboard,
    get_joke_keyboard, get_profile_keyboard, get_smart_settings_keyboard, get_country_keyboard,
    get_iran_cities_keyboard, get_iraq_cities_keyboard, get_language_keyboard, get_font_keyboard,
    get_font_en_keyboard, get_font_fa_keyboard,
)


def get_keyboard_builders():
    """Return the immutable canonical keyboard-constructor tuple."""
    return KEYBOARD_BUILDERS
