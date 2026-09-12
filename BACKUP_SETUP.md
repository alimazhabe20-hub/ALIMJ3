# سیستم بکاپ ALIMJ3 — Local + Telegram Private Channel

این نسخه بدون Cloudflare و Google Drive کار می‌کند. بکاپ اصلی خارج از Render داخل یک کانال خصوصی Telegram نگهداری می‌شود.

## 1) ساخت کانال
1. در Telegram یک Channel بساز.
2. Channel را روی **Private** بگذار.
3. ربات را Administrator کن.
4. اجازه ارسال پیام/فایل و **Pin Messages** را به ربات بده.

## 2) گرفتن Chat ID
Chat ID کانال را به شکل زیر در Render قرار بده:
`TELEGRAM_BACKUP_CHAT_ID=-1001234567890`

## 3) تنظیم Render
این متغیر کافی است (BOT_TOKEN از قبل در پروژه وجود دارد):

`TELEGRAM_BACKUP_CHAT_ID=-100...`

اختیاری:
- `BACKUP_INTERVAL_SECONDS=1800` یعنی هر ۳۰ دقیقه بکاپ.
- `TELEGRAM_BACKUP_INTERVAL_SECONDS=21600` یعنی هر ۶ ساعت یک کپی برای ادمین‌ها.
- GitHub می‌تواند به‌عنوان بکاپ دوم باقی بماند، ولی برای Telegram لازم نیست.

## 4) بکاپ خودکار
هر ۳۰ دقیقه: Local + Telegram Channel (+ GitHub اگر تنظیم شده).
همچنین هنگام shutdown/deploy تلاش مجدد انجام می‌شود.

## 5) Restore خودکار
آخرین بکاپ در کانال **Pin** می‌شود. اگر دیتابیس محلی خالی باشد، ربات `getChat` را صدا می‌زند، پیام پین‌شده را پیدا می‌کند، فایل را دانلود و سلامت SQLite را بررسی می‌کند و سپس Restore می‌کند. بنابراین بعد از ری‌استارت/Deploy نیازی به `/restore` نیست.

## 6) محدودیت
برای Restore خودکار، فایل بکاپ باید در محدوده دانلود Bot API باشد؛ پروژه به‌صورت محافظه‌کارانه سقف ۲۰MB برای دانلود خودکار گذاشته است. اگر دیتابیس بزرگ‌تر شد، Restore دستی `/restore` به‌عنوان راه اضطراری باقی می‌ماند.

## 7) تست
بعد از Deploy در لاگ باید چیزی شبیه این ببینی:
- `Telegram channel backup OK`
- `Restored from pinned Telegram backup` در اولین اجرای دیتابیس خالی

پیام بکاپ پین‌شده را از کانال حذف نکن. هر بکاپ جدید خودش جای نسخه قبلی را به‌عنوان Pointer می‌گیرد.
