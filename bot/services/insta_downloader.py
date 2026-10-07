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

# ===== merged from bot/services/insta_downloader_parts/part_001_is_instagram_url.py =====
# Auto-split part 1: is_instagram_url
def is_instagram_url(url: str) -> bool:
    host = (urlparse((url or "").strip()).hostname or "").lower().rstrip(".")
    return host == "instagram.com" or host.endswith(".instagram.com")

# ===== end merged part =====

# ===== merged from bot/services/insta_downloader_parts/part_002_is_social_url.py =====
# Auto-split part 2: is_social_url
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

# ===== end merged part =====

# ===== merged from bot/services/insta_downloader_parts/part_003__normalize_instagram_url.py =====
# Auto-split part 3: _normalize_instagram_url
def _normalize_instagram_url(url: str) -> str:
    """Strip tracking query params like the production ALIMJ3 normalizer."""
    p = urlparse((url or "").strip())
    host = (p.hostname or "").lower().rstrip(".")
    if host == "instagram.com" or host.endswith(".instagram.com"):
        return p._replace(query="").geturl()
    return url.strip()

# ===== end merged part =====

# ===== merged from bot/services/insta_downloader_parts/part_004_download_from_gallery.py =====
# Auto-split part 4: download_from_gallery
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

# ===== end merged part =====

# ===== merged from bot/services/insta_downloader_parts/services_insta_downloader_parts_part_005_download_from_ytdlp.py =====
# Auto-split part 5: download_from_ytdlp
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
            # Keep the fast path responsive while allowing segmented media
            # downloads to use several connections.
            "concurrent_fragment_downloads": max(1, min(int(os.getenv("YTDLP_CONCURRENT_FRAGMENTS", "4")), 8)),
            "http_chunk_size": min(max(int(os.getenv("YTDLP_HTTP_CHUNK_SIZE", str(10 * 1024 * 1024))), 0), 10 * 1024 * 1024),
            "buffersize": 1024 * 1024,
            "retries": 5,
            "fragment_retries": 5,
            "continuedl": True,
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

# ===== end merged part =====

# ===== merged from bot/services/insta_downloader_parts/part_006_download.py =====
# Auto-split part 6: download
async def download(url: str) -> str:
    """Download Instagram/social media with an Instagram web-API fallback.

    Instagram public Reel pages can redirect logged-out requests to the login
    page. For Instagram, try the web GraphQL media endpoint first, then keep
    the normal gallery-dl/yt-dlp fallbacks for environments where cookies or a
    different extractor path is available.
    """
    url = _normalize_instagram_url(url)
    errors: list[str] = []

    # Instagram's public web GraphQL endpoint can expose the media URL even
    # when the Reel HTML page redirects to /accounts/login/.
    if is_instagram_url(url):
        try:
            path = await _download_instagram_graphql(url)
            logger.info("insta_downloader: Instagram GraphQL ok -> %s", path)
            return path
        except Exception as e:
            errors.append(f"instagram-api: {e}")
            logger.warning("insta_downloader Instagram GraphQL failed: %s", e)

    # Keep the reference project's proven fallback order.
    try:
        path = await download_from_gallery(url)
        logger.info("insta_downloader: gallery-dl ok -> %s", path)
        return path
    except Exception as e:
        errors.append(f"Gallery: {e}")
        logger.warning("insta_downloader gallery-dl failed, falling back to yt-dlp: %s", e)

    try:
        path = await download_from_ytdlp(url)
        logger.info("insta_downloader: yt-dlp ok -> %s", path)
        return path
    except Exception as e:
        errors.append(f"yt-dlp: {e}")
        logger.warning("insta_downloader yt-dlp failed: %s", e)

    raise RuntimeError("\n".join(errors) if errors else "download failed")


async def _download_instagram_graphql(url: str) -> str:
    """Resolve a public Instagram Reel through the web GraphQL endpoint."""
    import asyncio as _asyncio
    import json as _json
    import os as _os
    import re as _re
    import tempfile as _tempfile
    from pathlib import Path as _Path
    from urllib.parse import urlparse as _urlparse

    shortcode_match = _re.search(r"/(?:reel|reels|p)/([A-Za-z0-9_-]+)", url)
    if not shortcode_match:
        raise RuntimeError("Instagram post/reel shortcode not found")
    shortcode = shortcode_match.group(1)

    def work() -> str:
        try:
            import requests
        except ImportError as exc:
            raise RuntimeError("requests is not installed") from exc

        session = requests.Session()
        session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/128.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })

        home = session.get("https://www.instagram.com/", timeout=20, allow_redirects=True)
        home.raise_for_status()
        csrf = session.cookies.get("csrftoken")
        if not csrf:
            raise RuntimeError("Instagram did not provide csrftoken")

        doc_id = _os.getenv("INSTAGRAM_GRAPHQL_DOC_ID", "27128499623469141").strip()
        variables = {
            "shortcode": shortcode,
            "__relay_internal__pv__PolarisAIGMMediaWebLabelEnabledrelayprovider": False,
        }
        response = session.post(
            "https://www.instagram.com/graphql/query",
            params={"doc_id": doc_id},
            data={"variables": _json.dumps(variables, separators=(",", ":"))},
            headers={
                "Accept": "*/*",
                "Content-Type": "application/x-www-form-urlencoded",
                "X-CSRFToken": csrf,
                "X-IG-App-ID": "936619743392459",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "https://www.instagram.com/",
            },
            timeout=25,
        )
        response.raise_for_status()
        payload = response.json()
        items = (((payload.get("data") or {}).get("xdt_api__v1__media__shortcode__web_info") or {}).get("items") or [])
        if not items:
            raise RuntimeError("Instagram GraphQL returned no media")

        media = items[0]
        candidates: list[str] = []
        for version in media.get("video_versions") or []:
            candidate = version.get("url")
            if candidate:
                candidates.append(candidate)
        if not candidates:
            # Some public posts expose the video URL in a nested image/media
            # structure. Keep this small fallback for API shape changes.
            for item in media.get("carousel_media") or []:
                for version in item.get("video_versions") or []:
                    candidate = version.get("url")
                    if candidate:
                        candidates.append(candidate)

        if not candidates:
            raise RuntimeError("Instagram response contained no video URL")

        media_url = candidates[0]
        out_dir = _Path(_tempfile.mkdtemp(prefix="alimj3_ig_"))
        out_path = out_dir / f"instagram_{shortcode}.mp4"
        with session.get(
            media_url,
            headers={"Referer": "https://www.instagram.com/", "Accept": "*/*"},
            stream=True,
            timeout=(20, 120),
        ) as download_response:
            download_response.raise_for_status()
            with out_path.open("wb") as fh:
                for chunk in download_response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        fh.write(chunk)

        if not out_path.is_file() or out_path.stat().st_size < 1024:
            raise RuntimeError("Instagram media download produced an empty file")
        return str(out_path)

    loop = _asyncio.get_running_loop()
    return await loop.run_in_executor(None, work)

# ===== end merged part =====

# ===== merged from bot/services/insta_downloader_parts/part_007_is_video_path.py =====
# Auto-split part 7: is_video_path
def is_video_path(path: str) -> bool:
    return Path(path).suffix.lower() in VIDEO_EXTS

# ===== end merged part =====

# ===== merged from bot/services/insta_downloader_parts/part_008_cleanup_path.py =====
# Auto-split part 8: cleanup_path
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

# ===== end merged part =====
