# ALIMJ3 Downloader Patch — gallery-dl integration

Based on `insta-downloader-bot` cascade:

1. **Instagram / TikTok / X / Pinterest / Reddit** → `gallery-dl` first, then `yt-dlp`, then direct HTTP
2. **Other sites** → `yt-dlp` first, then `gallery-dl`, then direct HTTP

## Install

```bash
pip install -U "gallery-dl>=1.27.0" "yt-dlp>=2025.08.27"
```

Optional cookies for Instagram (recommended when public extraction fails):

```env
DOWNLOADER_COOKIES_FILE=/path/to/cookies.txt
```

Export cookies from browser (Netscape format) using an extension like "Get cookies.txt LOCALLY".

## Files changed

- `bot/services/downloader.py` — gallery-dl engine + cascade + better Instagram errors
- `bot/handlers/v71_handlers.py` — accept `gallery_dl_missing` error code
- `requirements.txt` — added `gallery-dl>=1.27.0`

Copy these files into your ALIMJ3 project root structure and restart the bot.
