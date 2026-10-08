"""Safe Telegram media sending with optional Local Bot API Server support."""

import os
from pathlib import Path

from bot.logger import logger

STANDARD_MAX_UPLOAD_BYTES = 49 * 1024 * 1024
LOCAL_MAX_UPLOAD_BYTES = 2 * 1024 * 1024 * 1024


def local_mode_enabled() -> bool:
    return os.getenv("TELEGRAM_LOCAL_MODE", "false").strip().lower() in {"1", "true", "yes", "on"}


def max_upload_bytes() -> int:
    configured = int(os.getenv("TELEGRAM_MAX_UPLOAD_BYTES", "0") or 0)
    if configured > 0:
        return min(configured, LOCAL_MAX_UPLOAD_BYTES if local_mode_enabled() else STANDARD_MAX_UPLOAD_BYTES)
    return LOCAL_MAX_UPLOAD_BYTES if local_mode_enabled() else STANDARD_MAX_UPLOAD_BYTES


def ensure_sendable(path: str | Path) -> Path:
    p = Path(path)
    size = p.stat().st_size
    limit = max_upload_bytes()
    if size > limit:
        if local_mode_enabled():
            raise ValueError("telegram_upload_too_large")
        raise ValueError("telegram_standard_api_limit")
    return p


def upload_error_message(code: str) -> str:
    if code == "telegram_standard_api_limit":
        return (
            "📦 فایل دانلود شد اما Telegram Bot API معمولی اجازه ارسال این حجم را نمی‌دهد.\n"
            "برای فایل‌های بزرگ‌تر، Local Bot API Server را فعال کنید و "
            "TELEGRAM_LOCAL_MODE=true و آدرس سرور محلی را تنظیم کنید."
        )
    if code == "telegram_upload_too_large":
        return "📦 حجم فایل از سقف مجاز Local Bot API Server بیشتر است."
    return "❌ ارسال فایل به تلگرام ناموفق بود."


async def send_media(message, path: str | Path, *, title: str = "", caption: str = "📥 دانلودر فایل • روز زیبا") -> None:
    p = ensure_sendable(path)
    filename = (title or p.name)[:120]
    suffix = p.suffix.lower()
    video_exts = {".mp4", ".m4v", ".mov", ".webm", ".mkv"}
    audio_exts = {".mp3", ".m4a", ".aac", ".ogg", ".wav", ".opus"}

    # In local_mode the Bot API Server can read a local path directly. This is
    # required for large files; normal Bot API mode uses a regular file object.
    media = p if local_mode_enabled() else p.open("rb")
    close_after = not local_mode_enabled()
    try:
        if suffix in video_exts:
            await message.reply_video(video=media, caption=caption, supports_streaming=True, filename=filename)
        elif suffix in audio_exts:
            await message.reply_audio(audio=media, caption=caption, filename=filename)
        else:
            await message.reply_document(document=media, filename=filename, caption=caption)
    finally:
        if close_after:
            media.close()
