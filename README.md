# بسته پیشرفته گروه + سرعت + هوشمندی

## قابلیت‌های جدید
1. **Fast-path** — قیمت دلار/یورو/طلا/کریپتو و هوا بدون LLM (زیر ۱–۲ ثانیه)
2. **کش ۴۵ ثانیه‌ای** روی fast-path
3. **حافظه کوتاه گروه** (۴ نوبت آخر)
4. **تشخیص هوشمند** سؤال بدون منشن اجباری
5. **تنظیمات ادمین**: AI، پاسخ کوتاه، Fast-path، فقط منشن، فقط ادمین
6. **Force-join فقط پیوی**
7. **متریک** hit/miss fast-path
8. **ری‌اکشن ⚡** روی پاسخ fast-path
9. **Grounding** سخت در گروه + System Prompt ضد حدس
10. **استریم** و انیمیشن لودینگ

## نصب
فایل‌ها را با حفظ مسیر روی پروژه کپی کنید و ربات را ری‌استارت کنید.

## BotFather
Group Privacy = **Turn off**

## .env
```
GROUP_SMART_REPLY=true
GROUP_AI_ENABLED=true
BOT_USERNAME=almixprobot
GROUP_TRIGGER_PREFIXES=!,ربات,هوشمند
AI_TIMEOUT=25
AI_STREAM_CHUNK=120
AI_TOOL_TIMEOUT=12
HTTP_TIMEOUT=10
CACHE_TTL=60
```

## تست در گروه
- `قیمت دلار` → باید سریع با Fast-path جواب دهد
- `هوای تهران` → Fast-path
- سؤال مبهم → AI استریم
