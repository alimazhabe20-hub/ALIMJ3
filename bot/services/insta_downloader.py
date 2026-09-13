"""Instagram-oriented downloader cascade — ported from insta-downloader-bot.

Order (identical to the reference bot):
  1) gallery-dl
  2) yt-dlp

Returns a local file path. Caller is responsible for cleanup/send.
"""
from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from bot.logger import logger

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".m4v"}


def is_instagram_url(url: str) -> bool:
    host = (urlparse((url or "").strip()).hostname or "").lower().rstrip(".")
    return host == "instagram.com" or host.endswith(".instagram.com")


def is_social_url(url: str) -> bool:
    host = (urlparse((url or "").strip()).hostname or "").lower().rstrip(".")
    social = (
        "instagram.com",
        "cdninstagram.com",
        "tiktok.com",
        "vm.tiktok.com",
        "twitter.com",
        "x.com",
        "t.co",
        "facebook.com",
        "fb.watch",
        "reddit.com",
        "redd.it",
        "pinterest.com",
        "pin.it",
    )
    return any(host == h or host.endswith("." + h) for h in social)


def _normalize_instagram_url(url: str) -> str:
    """Strip tracking query params like the production ALIMJ3 normalizer."""
    p = urlparse((url or "").strip())
    host = (p.hostname or "").lower().rstrip(".")
    if host == "instagram.com" or host.endswith(".instagram.com"):
        return p._replace(query="").geturl()
    return url.strip()


async def download_from_gallery(url: str, temp_dir: str | None = None) -> str:
    """Exact logic from insta-downloader-bot/downloaders/gallery.py."""
    created = False
    if not temp_dir:
        temp_dir = tempfile.mkdtemp(prefix="alimj3_gdl_")
        created = True

    def work() -> str:
        cmd = ["gallery-dl", "-D", temp_dir, url]
        cookie = os.getenv("DOWNLOADER_COOKIES_FILE", "").strip()
        if cookie and Path(cookie).is_file():
            cmd.extend(["--cookies", cookie])
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            err = (result.stderr or result.stdout or "gallery-dl failed").strip()
            raise RuntimeError(err[:800] or "gallery-dl failed")

        files: list[str] = []
        for root, _dirs, filenames in os.walk(temp_dir):
            for name in filenames:
                if name.endswith((".json", ".txt", ".sqlite")):
                    continue
                files.append(os.path.join(root, name))
        if not files:
            raise RuntimeError("No file downloaded.")
        # Prefer largest file (video over tiny thumbnails)
        files.sort(key=lambda p: os.path.getsize(p), reverse=True)
        return files[0]

    try:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, work)
    except FileNotFoundError as exc:
        if created:
            shutil.rmtree(temp_dir, ignore_errors=True)
        raise RuntimeError(
            "gallery-dl نصب نیست. اجرا کنید: pip install -U gallery-dl"
        ) from exc
    except Exception:
        if created:
            shutil.rmtree(temp_dir, ignore_errors=True)
        raise


async def download_from_ytdlp(url: str, temp_dir: str | None = None) -> str:
    """Exact logic from insta-downloader-bot/downloaders/ytdlp.py (+ cookies/proxy)."""
    created = False
    if not temp_dir:
        temp_dir = tempfile.mkdtemp(prefix="alimj3_ydl_")
        created = True

    def work() -> str:
        try:
            import yt_dlp
        except ImportError as exc:
            raise RuntimeError("yt-dlp نصب نیست. pip install -U yt-dlp") from exc

        ydl_opts: dict = {
            "outtmpl": os.path.join(temp_dir, "%(title)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "merge_output_format": "mp4",
            "http_headers": {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Referer": "https://www.instagram.com/",
            },
        }
        cookie = os.getenv("DOWNLOADER_COOKIES_FILE", "").strip()
        if cookie and Path(cookie).is_file():
            ydl_opts["cookiefile"] = cookie
        proxy = os.getenv("DOWNLOADER_PROXY", "").strip()
        if proxy:
            ydl_opts["proxy"] = proxy

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info:
                raise RuntimeError("yt-dlp returned no info")
            if "requested_downloads" in info and info["requested_downloads"]:
                filename = info["requested_downloads"][0].get("filepath")
                if filename and os.path.exists(filename):
                    return filename
            filename = ydl.prepare_filename(info)
            if os.path.exists(filename):
                return filename
            # Fallback: any new media file in temp_dir
            candidates = []
            for root, _dirs, names in os.walk(temp_dir):
                for name in names:
                    candidates.append(os.path.join(root, name))
            if not candidates:
                raise RuntimeError("yt-dlp produced no file")
            candidates.sort(key=lambda p: os.path.getsize(p), reverse=True)
            return candidates[0]

    try:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, work)
    except Exception:
        if created:
            shutil.rmtree(temp_dir, ignore_errors=True)
        raise


async def download(url: str) -> str:
    """Cascade identical to insta-downloader-bot manager.download (without stub API)."""
    url = _normalize_instagram_url(url)
    errors: list[str] = []

    try:
        path = await download_from_gallery(url)
        logger.info("insta_downloader: gallery-dl ok → %s", path)
        return path
    except Exception as e:
        errors.append(f"Gallery: {e}")
        logger.warning("insta_downloader gallery-dl failed: %s", e)

    try:
        path = await download_from_ytdlp(url)
        logger.info("insta_downloader: yt-dlp ok → %s", path)
        return path
    except Exception as e:
        errors.append(f"yt-dlp: {e}")
        logger.warning("insta_downloader yt-dlp failed: %s", e)

    raise RuntimeError("\n".join(errors) if errors else "download failed")


def is_video_path(path: str) -> bool:
    return Path(path).suffix.lower() in VIDEO_EXTS


def cleanup_path(path: str | None) -> None:
    if not path:
        return
    try:
        p = Path(path)
        parent = p.parent
        p.unlink(missing_ok=True)
        if parent.exists() and parent.name.startswith("alimj3_") and not any(parent.iterdir()):
            parent.rmdir()
    except Exception:
        pass
