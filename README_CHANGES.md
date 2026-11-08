# فایل‌های جدید و تغییر یافته — پشتیبانی گروه + استریم لحظه‌ای

## فایل‌های جدید
- `bot/handlers/group_mode.py` — تشخیص گروه، تریگر منشن/ریپلای/پیشوند، خوش‌آمدگویی
- `bot/handlers/group_stream.py` — استریم حرفه‌ای لحظه‌ای با UI گروه

## فایل‌های تغییر یافته
- `bot/handlers/messages_routing.py` — گیت گروه در ابتدای هندلر متن
- `bot/handlers/messages_ai_router.py` — مسیر مستقیم AI برای گروه
- `bot/handlers/messages_ai.py` — استفاده از streamer گروه + cadence بهتر
- `bot/handlers/messages.py` — همان بهبودها (نسخه facade/legacy)
- `bot/main.py` — ثبت ChatMemberHandler و callbackهای گروه
- `bot/config.py` — تنظیمات GROUP_*
- `bot/utils/helpers.py` — تابع group_safe_markup
- `.env.example` — متغیرهای جدید گروه

## نصب
فایل‌ها را با حفظ مسیر روی پروژه اصلی کپی کنید.
