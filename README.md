# دانلودر اینستاگرام — عین insta-downloader-bot

## رفتار (مثل فایلی که فرستادید)

1. کاربر لینک اینستاگرام / تیک‌تاک / ... را می‌فرستد
2. پیام: `⏳ در حال دانلود...`
3. ترتیب موتورها:
   - **gallery-dl** (اول)
   - **yt-dlp** (دوم)
4. اگر ویدیو بود → `reply_video`
5. وگرنه → `reply_document`

## نصب ضروری

```bash
pip install -U "gallery-dl>=1.27.0" "yt-dlp>=2025.08.27"
```

بدون `gallery-dl` روی سرور، همان خطای قبلی تکرار می‌شود.

## کوکی (اگر اینستاگرام بلاک کرد)

```env
DOWNLOADER_COOKIES_FILE=/path/to/cookies.txt
```

کوکی Netscape از مرورگر (افزونه Get cookies.txt LOCALLY).

## فایل‌ها

- `bot/services/insta_downloader.py`  ← ماژول جدید (کپی منطق ربات شما)
- `bot/services/downloader.py`         ← اتصال cascade
- `bot/handlers/v71_handlers.py`       ← دانلود مستقیم برای لینک‌های سوشال
- `requirements.txt`

کپی کنید و ربات را ری‌استارت کنید.
