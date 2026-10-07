# ALIMJ3 Semantic Refactor V2 — 2026-10-07

این نسخه بر پایه `ALIMJ3-CLEAN-FINAL-2026-10-07.zip` ساخته شده است.

## هدف
- شکستن فایل‌های بزرگ بر اساس مسئولیت واقعی بدون حذف قابلیت‌ها.
- حفظ importهای قدیمی از طریق facadeهای سازگار.
- جلوگیری از نام فایل تکراری در کل پروژه (به‌جز `__init__.py`).
- نگه‌داشتن state/importهای مشترک در ماژول‌های common و سیم‌کشی namespace برای سازگاری کدهای قدیمی.

## حوزه‌های اصلی
- AI: config/providers/memory/media/voice/creative/router
- Messages: AI/routing/media/main
- Finance: chart/context/analysis/signals/tools
- Economic Calendar: parsing/providers/formatting/navigation
- Database: core/users/notifications/reminders/ai/calendar/stats
- Downloader: validation/providers/cache/public
- Shopping: models/parser/search/filter/public
- ICT: math/structure/zones/scenarios/public
- TA: indicators/structure/scoring
- Persistence: Telegram/GitHub/backup
- Platform V74/V75/V77: security/agent/performance/knowledge/providers/runtime و زیرسیستم‌های مرتبط
- AI Tools: basic/market/automation/agents

## اعتبارسنجی
- Python files: 339
- duplicate non-`__init__.py` basenames: 0
- AST parse errors: 0
- `__pycache__`/`.pyc`: excluded from release

## نکته مهم
سه فایل هنوز از 30KB بزرگ‌تر هستند، اما دلیل اصلی آن‌ها یک تابع/داده‌ی legacy بزرگ است:
- `bot/handlers/messages_routing.py` — `_text_handler_inner`
- `bot/handlers/callbacks_actions/handle_economic_calendar.py` — handler اقتصادی بزرگ
- `bot/utils/utils_events_common.py` — داده/ثابت‌های تقویمی

این سه مورد عمداً با شکستن کورکورانه‌ی بدنه‌ی توابع تغییر داده نشده‌اند تا رفتار ربات آسیب نبیند. مرحله بعدی باید refactor درون‌تابعی تست‌محور باشد، نه صرفاً تکه‌تکه‌کردن متن.
