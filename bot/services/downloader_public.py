"""downloader: public responsibilities."""
from .downloader_common import *  # noqa: F401,F403
from . import downloader_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


class DownloadError(Exception):
    pass

async def download(url: str, *, mode: str = "best", user_id: int | None = None, progress_cb=None, use_cache: bool = True, preflight: bool = True) -> dict:
    if mode not in {"best", "1080p", "720p", "480p", "audio"}:
        mode = "best"
    url = _normalize_media_url(url)
    if _is_blocked_media_url(url):
        raise DownloadError("unsupported")
    if preflight:
        url = _preflight_redirects(url)
    if use_cache:
        cached = _cache_get(url, mode)
        if cached:
            return cached
    user_sem = _user_sem(user_id)
    async with _global_sem:
        async with user_sem:
            # Instagram / social: exact cascade from insta-downloader-bot
            # (gallery-dl → yt-dlp), before the generic ALIMJ3 engines.
            try:
                from bot.services.insta_downloader import is_social_url, download as insta_download, is_video_path
            except Exception:
                is_social_url = lambda _u: False  # type: ignore
                insta_download = None
                is_video_path = lambda _p: False  # type: ignore

            if insta_download and is_social_url(url):
                try:
                    file_path = await insta_download(url)
                    p = Path(file_path)
                    size = p.stat().st_size if p.exists() else 0
                    if size <= 0:
                        raise DownloadError("failed")
                    if size > MAX_BYTES:
                        try:
                            p.unlink(missing_ok=True)
                        except Exception as exc:
                            logger.debug("oversized social file cleanup failed: %s", exc)
                        raise DownloadError("too_large")
                    result = {
                        "path": str(p),
                        "title": _safe_name(p.stem or "instagram_media"),
                        "size": size,
                        "content_type": p.suffix.lstrip(".") or "bin",
                        "method": "insta-cascade",
                        "mode": mode,
                        "is_video": is_video_path(str(p)),
                    }
                    _cache_put(result, url, mode)
                    return result
                except DownloadError:
                    raise
                except Exception as exc:
                    logger.warning("insta-cascade failed, falling back to generic engines: %s", exc)
                    # fall through to generic yt-dlp / direct

            outdir = Path(tempfile.mkdtemp(prefix="alimj3_dl_"))
            try:
                used_external = False
                try:
                    result = await _ytdlp(url, outdir, mode=mode, progress_cb=progress_cb)
                except DownloadError as first:
                    if str(first) in {"site_blocked", "rate_limited", "access_restricted", "too_large", "yt_dlp_missing"}:
                        if str(first) == "yt_dlp_missing" and mode == "best":
                            filename = _safe_name(Path(urlparse(url).path).name or "download.bin")
                            result = await _direct(url, outdir / filename)
                        else:
                            # Last chance: try external even for non- if configured
                            if not used_external and _external_providers_configured():
                                ext = await _try_external_providers(url, outdir, mode)
                                if ext:
                                    result = ext
                                else:
                                    raise
                            else:
                                raise
                    else:
                        filename = _safe_name(Path(urlparse(url).path).name or "download.bin")
                        result = await _direct(url, outdir / filename)
                _cache_put(result, url, mode)
                return result
            except Exception:
                shutil.rmtree(outdir, ignore_errors=True)
                raise

def cleanup(path: str | None):
    if not path:
        return
    try:
        p = Path(path)
        # Cached files are intentionally retained.
        if p.resolve().parent == CACHE_DIR.resolve():
            return
        parent = p.parent
        p.unlink(missing_ok=True)
        if parent.name.startswith("alimj3_dl_") and parent.exists() and not any(parent.iterdir()):
            parent.rmdir()
    except Exception as exc:
        logger.debug("non-fatal exception: %s", exc)

def user_message(code: str) -> str:
    return {
        "invalid_url": "❌ لینک معتبر http/https ارسال کنید.",
        "blocked_host": "❌ این مقصد به دلایل امنیتی قابل دریافت نیست.",
        "dns_error": "❌ دامنه قابل دسترسی نیست.",
        "rate_limited": "⏳ سایت موقتاً درخواست‌ها را محدود کرده است. بعداً دوباره امتحان کنید.",
        "site_blocked": "🚫 سایت دسترسی دانلود را مسدود کرده یا CAPTCHA/ورود لازم دارد. امکان دور زدن محدودیت سایت در ربات وجود ندارد.",
        "access_restricted": "🔒 این محتوا خصوصی/محدود است و بدون دسترسی مجاز قابل دریافت نیست.",
        "unsupported": "⚠️ این لینک توسط موتور دانلود پشتیبانی نشد.",
        "too_large": f"📦 فایل برای ارسال مستقیم بیش از حد بزرگ است. سقف ربات {MAX_BYTES // (1024*1024)}MB است.",
        "yt_dlp_missing": "⚠️ موتور yt-dlp نصب نشده است. requirements را نصب کنید.",
        "gallery_dl_missing": "⚠️ موتور gallery-dl نصب نشده است.\nدستور: pip install -U gallery-dl",
        "failed": "❌ دانلود ناموفق بود.\nسایت پاسخ قابل دریافت برنگرداند.",
    }.get(code, "❌ دانلود ناموفق بود.")
