# Semantic Refactor — 2026-10-07

این مرحله بعد از پاک‌سازی ساختاری انجام شد و چند تابع بزرگ را واقعاً بر اساس مسئولیت به فایل‌های مستقل منتقل کرد، در حالی که مسیرهای import قدیمی به‌عنوان facade حفظ شدند.

## Shopping

- `bot/features/market/shopping_parts/shopping_parser.py`
  - نرمال‌سازی اعداد فارسی/عربی
  - تشخیص بودجه
  - تشخیص موبایل
  - تشخیص سایت و بازار خارجی
  - استخراج قیمت و اعتبار عنوان
- `bot/features/market/shopping_parts/shopping_provider.py`
  - Bing
  - Torob live API
  - Digikala live API
- `bot/features/market/shopping_parts/shopping_formatter.py`
  - قالب‌بندی نتیجه زنده و قیمت‌های تأییدشده
- `bot/features/market/shopping_parts/shopping_search.py`
  - orchestration جستجوی زنده ایران/جهانی
- `part_016_search_shopping_live.py`
  - به facade سازگار با importهای قبلی تبدیل شد.

## AI Providers

- `bot/services/ai_providers_parts/ai_gemini_provider.py`
  - پیاده‌سازی Gemini function-calling
- `bot/services/ai_providers_parts/ai_openai_provider.py`
  - پیاده‌سازی OpenAI-compatible provider
- فایل‌های legacy مربوطه facade باقی مانده‌اند تا importهای قدیمی نشکنند.

## AI Tool Registry

- `bot/services/ai_tools_parts/ai_tool_registry.py`
  - ثبت ابزارهای داخلی AI از تابع بزرگ قبلی جدا شد.
- تابع قدیمی `_register_builtin_tools` به wrapper سازگار تبدیل شد.

## Crypto Analysis

- `bot/features/market/finance_crypto_parts/crypto_analyzer.py`
  - منطق تحلیل حرفه‌ای کریپتو از دو تعریف تکراری جدا شد.
- هر دو مسیر قدیمی `analyze_crypto` به implementation مشترک جدید وصل شدند.

## Loader cleanup

مسیرهای loader تولیدشده در نسخه پاک‌شده نیز اصلاح شدند تا chunkها نسبت به directory واقعی خودشان resolve شوند.

## Validation

- AST errors: `0`
- duplicate non-`__init__.py` basenames: `0`
- broken modular loader targets: `0`
- `compileall bot`: موفق

## نکته مهم

چند router بسیار بزرگ هنوز عمداً دست‌نخورده‌اند، از جمله `button_handler` و `_text_handler_inner`. شکستن این‌ها نیاز به تفکیک رفتاری callback/message به domain handlerهای مستقل دارد و نباید با تقسیم مکانیکی انجام شود؛ چون احتمال تغییر ترتیب شرط‌ها و رفتار ربات بالاست. این‌ها مرحله بعدی refactor معنایی هستند.
