"""لودینگ و خطای یکسان برای بازار، دانلودر و سایر بخش‌های شبکه‌ای."""
from __future__ import annotations

from typing import Optional

from telegram import Message
from telegram.ext import ContextTypes

# کلید → متن لودینگ
LOADING_TEXT = {
    "market": "⏳ در حال دریافت قیمت‌های بازار…",
    "crypto_top": "⏳ در حال دریافت لیست ارزهای دیجیتال…",
    "crypto_analyze": "⏳ در حال دریافت تحلیل {symbol}…",
    "gold": "⏳ در حال دریافت تحلیل زنده طلا / XAUUSD…",
    "economic": "⏳ در حال دریافت تقویم اقتصادی…",
    "currency": "⏳ در حال تبدیل ارز…",
    "download_check": "⏳ در حال بررسی لینک…",
    "download_file": "⏳ در حال دانلود فایل…",
    "download_upload": "⏳ در حال ارسال فایل به تلگرام…",
    "download_social": "⏳ در حال دریافت از شبکه اجتماعی…",
    "generic": "⏳ لطفاً چند لحظه صبر کنید…",
}

# کلید → عنوان خطای کاربرپسند
ERROR_TITLE = {
    "market": "دریافت قیمت بازار",
    "crypto_top": "دریافت لیست ارزها",
    "crypto_analyze": "تحلیل ارز دیجیتال",
    "gold": "تحلیل طلا",
    "economic": "تقویم اقتصادی",
    "currency": "تبدیل ارز",
    "download": "دانلود فایل",
    "download_check": "بررسی لینک",
    "download_file": "دانلود فایل",
    "download_upload": "ارسال فایل",
    "generic": "انجام درخواست",
}


def loading_text(key: str = "generic", **fmt) -> str:
    tpl = LOADING_TEXT.get(key) or LOADING_TEXT["generic"]
    try:
        return tpl.format(**fmt) if fmt else tpl
    except Exception:
        return tpl


def error_text(
    key: str = "generic",
    *,
    detail: Optional[str] = None,
    hint: Optional[str] = None,
) -> str:
    title = ERROR_TITLE.get(key) or ERROR_TITLE["generic"]
    lines = [
        "⚠️ مشکلی پیش آمد",
        "・ ・ ・ ・ ・",
        f"بخش: {title}",
    ]
    if detail:
        d = str(detail).strip()
        if len(d) > 180:
            d = d[:177] + "…"
        # فیلتر traceback خام
        if "Traceback" in d or "File \"" in d:
            d = "خطای داخلی سرور"
        lines.append(f"جزئیات: {d}")
    lines.append("")
    lines.append(hint or "چند ثانیه بعد دوباره امتحان کن. اگر ادامه داشت از منو یک‌بار خارج و دوباره وارد شو.")
    return "\n".join(lines)


async def send_loading(message: Message, key: str = "generic", **fmt) -> Optional[Message]:
    """پیام لودینگ بفرست؛ در صورت خطا None."""
    try:
        return await message.reply_text(loading_text(key, **fmt))
    except Exception:
        return None


async def edit_status(notice: Optional[Message], text: str, **kwargs) -> bool:
    """ویرایش پیام لودینگ به متن نهایی. False اگر نشد."""
    if notice is None:
        return False
    try:
        await notice.edit_text(text, **kwargs)
        return True
    except Exception:
        return False


async def safe_delete(notice: Optional[Message]) -> None:
    if notice is None:
        return
    try:
        await notice.delete()
    except Exception:
        pass


async def finish_or_reply(
    notice: Optional[Message],
    message: Message,
    text: str,
    **kwargs,
) -> Message:
    """اگر edit ممکن بود همان notice؛ وگرنه پیام جدید."""
    if notice is not None:
        ok = await edit_status(notice, text, **kwargs)
        if ok:
            return notice
        await safe_delete(notice)
    return await message.reply_text(text, **kwargs)


async def fail_notice(
    notice: Optional[Message],
    message: Message,
    key: str = "generic",
    *,
    detail: Optional[str] = None,
    hint: Optional[str] = None,
    reply_markup=None,
) -> Message:
    text = error_text(key, detail=detail, hint=hint)
    kwargs = {}
    if reply_markup is not None:
        kwargs["reply_markup"] = reply_markup
    return await finish_or_reply(notice, message, text, **kwargs)
