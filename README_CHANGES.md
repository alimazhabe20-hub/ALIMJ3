# تغییرات گروه v2

## جدید
- bot/handlers/group_settings.py — تنظیمات هر گروه در SQLite
- bot/handlers/group_commands.py — /ask /ai /groupsettings + callbackها

## به‌روز شده
- bot/handlers/group_mode.py — ادمین، تنظیمات، خوش‌آمدگویی
- bot/handlers/group_stream.py — انیمیشن لودینگ، پاسخ کوتاه، پرامپت ضدتوهم
- bot/handlers/messages_*.py — گیت گروه + چک AI
- bot/main.py — ثبت دستورات و کالبک‌ها
- bot/config.py — GROUP_*
- bot/services/ai_service*.py — تقویت ضد حدس‌زدن
- bot/utils/helpers.py — group_safe_markup
- .env.example

## دستورات گروه
- /ask سؤال   یا   /ai سؤال
- /groupsettings  (فقط ادمین) — روشن/خاموش AI و پاسخ کوتاه
