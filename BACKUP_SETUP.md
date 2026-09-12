# پشتیبان‌گیری خودکار و امن دیتابیس

این نسخه بکاپ دیتابیس را به‌صورت خودکار در چند لایه انجام می‌دهد:

- SQLite snapshot محلی و چرخشی
- GitHub در یک Repository خصوصی
- کپی مستقل در Telegram برای ادمین‌ها
- قبل از shutdown/deploy نیز backup اجرا می‌شود
- اگر دیتابیس محلی خالی باشد، GitHub برای restore خودکار بررسی می‌شود
- دیتابیس خالی یا خراب روی بکاپ معتبر overwrite نمی‌شود
- فایل GitHub به صورت gzip ذخیره می‌شود تا حجم کمتر شود

## تنظیم GitHub در Render

### 1) یک Repository خصوصی بساز

مثلاً:

`ALIMJ-backups`

Repository بکاپ باید **Private** باشد؛ دیتابیس شامل اطلاعات کاربران است و نباید در Repository عمومی قرار بگیرد.

### 2) Token بساز

برای GitHub Fine-grained Personal Access Token، فقط Repository بکاپ را انتخاب کن و برای آن دسترسی Contents را روی **Read and write** قرار بده.

### 3) Environment Variables را در Render تنظیم کن

```text
GITHUB_TOKEN=<token>
GITHUB_REPO=<github-username>/ALIMJ-backups
GITHUB_BRANCH=main
GITHUB_DB_FILE=backups/latest.db.gz
GITHUB_BACKUP_RETRIES=4
GITHUB_BACKUP_BACKOFF=1.5
BACKUP_INTERVAL_SECONDS=1800
TELEGRAM_BACKUP_INTERVAL_SECONDS=21600
```

`GITHUB_REPO` باید به شکل `owner/repository` باشد. URL کامل لازم نیست.

### زمان‌بندی

- بکاپ local + GitHub: هر ۳۰ دقیقه
- بکاپ Telegram: هر ۶ ساعت
- ۲ دقیقه بعد از startup یک بکاپ local/GitHub انجام می‌شود
- ۵ دقیقه بعد از startup یک بکاپ Telegram انجام می‌شود
- هنگام shutdown/deploy نیز backup فوری اجرا می‌شود

### نکته مهم درباره Render

اگر برای سرویس Render دیسک Persistent نداری، روی `/data` برای حفظ دائمی دیتابیس حساب نکن. در این حالت GitHub خصوصی و Telegram باید به عنوان کپی‌های خارج از سرویس استفاده شوند.

### تست

بعد از تنظیم متغیرها، ربات را restart کن و در log باید چیزی شبیه این ببینی:

```text
local:OK | github:OK (...)
```

اگر Repository یا Token اشتباه باشد، پیام خطا اکنون دقیق‌تر است؛ مثلاً:

```text
GitHub 404: repository پیدا نشد یا Token به آن دسترسی ندارد
```

و دیگر فقط `Not Found` مبهم نمایش داده نمی‌شود.
