"""Cobalt media downloader provider for ALIMJ3.

Supports: YouTube, TikTok, Instagram, Twitter/X, Facebook, Reddit, ...
Docs: https://github.com/imputnet/cobalt/blob/main/docs/api.md

Configure:
  COBALT_API_URL  — e.g. https://api.cobalt.tools  or your self-hosted instance
  COBALT_API_KEY  — optional Bearer token if instance requires auth
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from bot.logger import logger

# Public hosted API may use bot-protection; self-host is recommended for production.
COBALT_API_URL = os.getenv("COBALT_API_URL", "https://api.cobalt.tools").rstrip("/")
COBALT_API_KEY = os.getenv("COBALT_API_KEY", "").strip()
COBALT_TIMEOUT = float(os.getenv("COBALT_TIMEOUT", "45"))

_SUPPORTED_HOSTS = (
    "youtube.com",
    "youtu.be",
    "tiktok.com",
    "vm.tiktok.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "t.co",
    "facebook.com",
    "fb.watch",
    "reddit.com",
    "redd.it",
    "pinterest.com",
    "pin.it",
    "vimeo.com",
    "soundcloud.com",
    "dailymotion.com",
    "bilibili.com",
    "streamable.com",
    "twitch.tv",
    "bluesky",
    "bsky.app",
)


def is_cobalt_url(url: str) -> bool:
    host = (urlparse((url or "").strip()).hostname or "").lower().rstrip(".")
    if not host:
        return False
    return any(host == h or host.endswith("." + h) or h in host for h in _SUPPORTED_HOSTS)


def _headers() -> dict[str, str]:
    h = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ALIMJ3-Bot/1.0",
    }
    if COBALT_API_KEY:
        h["Authorization"] = f"Bearer {COBALT_API_KEY}"
    return h


async def cobalt_resolve(url: str, *, audio_only: bool = False, quality: str = "720") -> dict[str, Any]:
    """Call Cobalt API and return parsed result.

    Possible return shapes:
      {"status": "tunnel"|"redirect", "url": "...", "filename": "..."}
      {"status": "picker", "items": [...]}
      {"status": "error", "error": "..."}
    """
    body: dict[str, Any] = {
        "url": url.strip(),
        "videoQuality": quality,
        "filenameStyle": "pretty",
    }
    if audio_only:
        body["downloadMode"] = "audio"
        body["audioFormat"] = "mp3"
    else:
        body["downloadMode"] = "auto"

    endpoints = [
        f"{COBALT_API_URL}/",  # v7+
        f"{COBALT_API_URL}/api/json",  # older
    ]

    last_err = "unknown"
    async with httpx.AsyncClient(timeout=COBALT_TIMEOUT, follow_redirects=True) as client:
        for ep in endpoints:
            try:
                r = await client.post(ep, json=body, headers=_headers())
                if r.status_code == 404:
                    continue
                if r.status_code >= 400:
                    last_err = f"HTTP {r.status_code}: {r.text[:200]}"
                    # try parse error json
                    try:
                        ej = r.json()
                        last_err = str(
                            ej.get("error")
                            or (ej.get("error") or {}).get("code")
                            or ej.get("text")
                            or last_err
                        )
                    except Exception:
                        pass
                    continue
                data = r.json()
                if not isinstance(data, dict):
                    last_err = "invalid json"
                    continue
                return data
            except Exception as e:
                last_err = str(e)[:200]
                logger.debug("cobalt endpoint %s: %s", ep, e)
                continue

    return {"status": "error", "error": last_err}


async def cobalt_download(
    url: str,
    outdir: Path,
    *,
    audio_only: bool = False,
    quality: str = "720",
) -> dict[str, Any]:
    """Resolve via Cobalt then download file to outdir.

    Returns dict compatible with bot downloader:
      path, filename, method, mode, size
    Raises RuntimeError on failure.
    """
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    data = await cobalt_resolve(url, audio_only=audio_only, quality=quality)
    status = str(data.get("status") or "").lower()

    if status in {"error", "rate-limit"}:
        raise RuntimeError(str(data.get("error") or data.get("text") or "cobalt error"))

    # picker: several items — take first video-like
    if status == "picker":
        items = data.get("picker") or data.get("items") or []
        file_url = None
        filename = "media.bin"
        for it in items:
            if not isinstance(it, dict):
                continue
            u = it.get("url") or it.get("link")
            if u:
                file_url = u
                filename = it.get("filename") or filename
                break
        if not file_url:
            raise RuntimeError("cobalt picker empty")
    elif status in {"tunnel", "redirect", "stream", "success", "local-processing"}:
        file_url = data.get("url") or data.get("tunnel") or data.get("download_url")
        filename = data.get("filename") or "media.bin"
        if not file_url:
            raise RuntimeError("cobalt returned no url")
    else:
        # some instances return url at top level
        file_url = data.get("url")
        filename = data.get("filename") or "media.bin"
        if not file_url:
            raise RuntimeError(f"cobalt status={status or '?'}")

    # sanitize filename
    filename = re.sub(r"[^\w.\- \u0600-\u06FF]+", "_", str(filename)).strip("._") or "media.bin"
    dest = outdir / filename

    async with httpx.AsyncClient(timeout=COBALT_TIMEOUT, follow_redirects=True) as client:
        async with client.stream("GET", file_url, headers={"User-Agent": "ALIMJ3-Bot/1.0"}) as resp:
            if resp.status_code >= 400:
                raise RuntimeError(f"download HTTP {resp.status_code}")
            size = 0
            max_bytes = int(os.getenv("DOWNLOADER_MAX_BYTES", str(200 * 1024 * 1024)))
            with open(dest, "wb") as f:
                async for chunk in resp.aiter_bytes(64 * 1024):
                    size += len(chunk)
                    if size > max_bytes:
                        raise RuntimeError("file too large")
                    f.write(chunk)

    return {
        "path": str(dest),
        "filename": filename,
        "method": "cobalt",
        "mode": "audio" if audio_only else "video",
        "size": dest.stat().st_size,
        "url": url,
    }


async def cobalt_download_link_only(url: str, *, audio_only: bool = False) -> str:
    """Only resolve direct media URL (no local save). Useful to send link to user."""
    data = await cobalt_resolve(url, audio_only=audio_only)
    status = str(data.get("status") or "").lower()
    if status == "picker":
        for it in data.get("picker") or []:
            if isinstance(it, dict) and it.get("url"):
                return str(it["url"])
        raise RuntimeError("no media in picker")
    link = data.get("url") or data.get("tunnel")
    if not link:
        raise RuntimeError(str(data.get("error") or "no url"))
    return str(link)
