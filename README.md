# 🌤️ ROOZE ZIBA — روز زیبا

<p align="center">
  <strong>🤖 Persian AI • 🌐 Live Web • 📊 Markets • 🌦️ Weather • 🗓️ Calendar • 📥 Downloader</strong>
</p>

<p align="center">
  <em>یک دستیار فارسی که فقط جواب نمی‌دهد؛ می‌فهمد، جست‌وجو می‌کند و به‌روز می‌ماند.</em>
</p>

---

## ✨ What is Rooze Ziba?

**Rooze Ziba (روز زیبا)** یک Telegram Bot مدرن، ماژولار و فارسی است که برای تبدیل شدن به یک **دستیار هوشمند همه‌کاره** ساخته شده.

تمرکز پروژه روی سه چیز است:

> **⚡ سریع‌تر — 🧠 هوشمندتر — 🌐 به‌روزتر**

از گفت‌وگوی AI و Web Search گرفته تا بازارهای مالی، تقویم اقتصادی، آب‌وهوا و دانلود محتوا؛ همه‌چیز در یک تجربه‌ی یکپارچه.

---

## 🔥 Features

| بخش | قابلیت‌ها |
|---|---|
| 🤖 **AI** | گفت‌وگوی هوشمند فارسی، Routing، Fallback، مدیریت خطا و پاسخ پویا |
| 🌐 **Web Search** | جست‌وجوی اطلاعات جدید با چند Provider و مسیرهای جایگزین |
| 🧠 **Freshness** | تشخیص سؤال‌های وابسته به زمان و جلوگیری از تکیه‌ی کورکورانه به اطلاعات قدیمی |
| 📊 **Market** | کریپتو، تحلیل تکنیکال، Price Action، RSI، ADX، حمایت/مقاومت و Fear & Greed |
| 🗓️ **Economic Calendar** | رویدادهای اقتصادی، اهمیت، Actual / Forecast / Previous و زمان تهران |
| 🌦️ **Weather** | اطلاعات کاربردی آب‌وهوا با رابط فارسی |
| 📥 **Downloader** | YouTube، Instagram، Story و سرویس‌های سازگار |
| 🧩 **Modular** | ماژول‌های مستقل برای توسعه و نگهداری آسان‌تر |
| 🛡️ **Reliable** | Timeout، Retry، Fallback و مدیریت خطا |

---

## 🧠 AI That Knows When to Search

یکی از قسمت‌های جذاب Rooze Ziba، **Freshness Engine** است.

همه‌ی سؤال‌ها نیاز به Web Search ندارند؛ اما بعضی سؤال‌ها بدون اطلاعات تازه جواب قابل اعتمادی ندارند.

مثلاً:

```text
❓ جدیدترین آیفون چیست؟
❓ قیمت بیت‌کوین الان چقدر است؟
❓ بهترین گوشی زیر ۵۰ میلیون چیست؟
❓ نتیجه بازی دیشب چه شد؟
❓ رئیس‌جمهور فعلی آمریکا کیست؟
```

سیستم می‌تواند چنین درخواست‌هایی را تشخیص دهد:

```text
User
  │
  ▼
🧠 Request Detection
  │
  ├── General Question ──────► 🤖 AI
  │
  └── Fresh / Time-Sensitive
             │
             ▼
        🌐 Web Search
             │
             ▼
        🧹 Fresh Results
             │
             ▼
        🤖 AI Answer
```

هدف:

> **کمتر حدس بزن؛ بیشتر بررسی کن.**

---

## 🌐 Multi-Provider Web Search

برای کاهش وابستگی به یک سرویس، سیستم جست‌وجو قابلیت استفاده از چند Provider را دارد:

```text
Tavily
   ↓
Brave Search
   ↓
Serper
   ↓
SearXNG
   ↓
DuckDuckGo
```

اگر یک مسیر در دسترس نباشد، سیستم می‌تواند به مسیر جایگزین برود.

### Why it matters

- ⚡ دسترسی بهتر
- 🔄 Fallback
- 🛡️ کاهش وابستگی
- 🌍 منابع متنوع‌تر
- 🧠 پاسخ‌های تازه‌تر

---

# 📊 Market Intelligence

بخش Market برای ارائه‌ی اطلاعات و تحلیل بازار طراحی شده است.

### 🪙 Crypto

- قیمت لحظه‌ای
- اطلاعات بازار
- RSI (14)
- ADX (14)
- Fear & Greed
- Support / Resistance
- Price Action
- ساختار بازار
- تحلیل چند تایم‌فریمی

### 📈 Smart Analysis

سیستم می‌تواند داده‌های بازار را ترکیب کرده و یک تحلیل ساختاریافته ارائه کند.

```text
Market Data
     +
Technical Indicators
     +
Price Action
     +
Market Sentiment
     ↓
🧠 Smart Analysis
```

---

# 🗓️ Economic Calendar

تقویم اقتصادی برای دنبال کردن رویدادهای مهم بازار:

- 🕐 زمان با `Asia/Tehran`
- 💵 ارز رویداد
- 🔥 اهمیت
- 📢 Actual
- 🔮 Forecast
- 🕘 Previous
- 📰 رویدادهای اقتصادی
- 🧠 بررسی اثر احتمالی روی بازار

---

# 🌦️ Weather

اطلاعات آب‌وهوایی در قالبی ساده و فارسی:

- 🌡️ دما
- 💧 رطوبت
- 💨 باد
- ☁️ وضعیت آسمان
- 🌧️ بارش
- 📍 موقعیت

---

# 📥 Downloader

یک Downloader چندمنظوره برای پردازش لینک‌های مختلف.

### Supported

```text
▶️ YouTube
📸 Instagram
📱 Instagram Stories
🔗 Other compatible sources
```

### Designed for

- ⚡ سرعت
- 🔄 Fallback
- 🛠️ مدیریت خطا
- 📦 فایل‌های حجیم
- 🧹 مدیریت فایل‌های موقت

---

# 🧩 Architecture

Rooze Ziba بر پایه‌ی **Modular Architecture** ساخته شده.

```text
ALIMJ3-main/
│
├── bot/
│   ├── handlers/
│   ├── services/
│   ├── features/
│   │   ├── market/
│   │   ├── weather/
│   │   └── ...
│   ├── utils/
│   └── main.py
│
├── tests/
├── requirements.txt
├── .env.example
└── README.md
```

### 🧱 Modular Rule

فایل‌های اصلی تا جای ممکن:

**کوچک + پایدار + قابل اعتماد**

باقی قابلیت‌ها ترجیحاً در ماژول‌های مستقل توسعه داده می‌شوند.

نتیجه:

```text
🧩 Smaller Modules
      +
🔒 Stable Core
      +
🚀 Easier Development
      =
💎 Cleaner Project
```

---

# 🔐 Environment

اطلاعات حساس را داخل کد قرار ندهید.

از Environment Variables استفاده کنید:

```env
BOT_TOKEN=
AI_API_KEY=
TAVILY_API_KEY=
BRAVE_API_KEY=
SERPER_API_KEY=
SEARXNG_URL=
```

نمونه تنظیمات در:

```text
.env.example
```

> ⚠️ Token و API Key را Commit نکنید.

---

# 🧪 Testing

برای اجرای تست‌ها:

```bash
pytest
```

برای بررسی Syntax:

```bash
python -m compileall .
```

---

# ☁️ Deployment

اجرای Production:

```bash
python -m bot.main
```

Python:

```text
3.12+
```

مناسب برای محیط‌های Cloud مانند Render.

---

# 🛡️ Reliability First

Rooze Ziba تا جای ممکن به یک سرویس وابسته نمی‌ماند.

الگوی کلی:

```text
Primary
  │
  ├── ✅ Success → Done
  │
  └── ❌ Failure
          │
          ▼
       Fallback
          │
          ├── ✅ Success → Done
          │
          └── ❌ Failure
                  │
                  ▼
             Safe Response
```

---

# 🎨 UX

طراحی رابط کاربری با تمرکز روی تجربه‌ی فارسی:

- 🇮🇷 Persian-first
- 🔘 Inline Buttons
- 🧭 Navigation
- 🔙 Back
- ⚡ Interactive Responses
- 📱 Mobile Friendly
- 📊 Clean Data Presentation

---

# 🧭 Development Principles

قبل از هر تغییر:

- ❌ قابلیت فعلی حذف نشود
- 🔒 فایل‌های پایدار بی‌دلیل دستکاری نشوند
- 🧩 قابلیت جدید تا حد امکان ماژولار باشد
- 🛠️ خطاها مدیریت شوند
- 🌐 داده‌ی قدیمی با داده‌ی لحظه‌ای اشتباه نشود
- 🧪 تغییرات قابل تست باشند
- 📦 وابستگی جدید فقط در صورت نیاز واقعی اضافه شود

---

# 💙 The Idea

روز زیبا قرار نیست فقط یک Bot دیگر باشد.

هدف این است:

```text
        👤 User
           │
           ▼
     🌤️ Rooze Ziba
           │
    ┌──────┼──────┐
    ▼      ▼      ▼
   🤖     🌐     📊
   AI    Web   Market
    │      │      │
    └──────┼──────┘
           ▼
      🧠 Smart Core
           │
           ▼
      ⚡ Better Answer
```

> **یک دستیار فارسی که وقتی لازم است فکر می‌کند، وقتی لازم است جست‌وجو می‌کند، و وقتی لازم است از داده‌ی تازه استفاده می‌کند.**

---

## ⭐ Rooze Ziba

<p align="center">

### 🌤️ روز زیبا؛ هوشمندتر، سریع‌تر، به‌روزتر.

**Rooze Ziba / ALIMJ**

</p>
