"""شناسایی آهنگ از صدا + دریافت lyrics.

جریان:
  1) AudD  → artist / title
  2) LRCLIB → متن ترانه (بدون کلید)
  3) (اختیاری) Genius اگر GENIUS_ACCESS_TOKEN باشد

Env:
  AUDD_API_TOKEN   — الزامی برای شناسایی
  GENIUS_ACCESS_TOKEN — اختیاری
"""
from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from typing import Optional

from bot.logger import logger


def _http_json(url: str, *, data: bytes | None = None, headers: dict | None = None, method: str = "GET", timeout: int = 30) -> dict:
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw) if raw else {}


def recognize_audd(audio_bytes: bytes, *, filename: str = "voice.ogg", mime: str = "audio/ogg") -> Optional[dict]:
    """شناسایی با AudD. خروجی: {artist, title, album, song_link} یا None."""
    token = (os.getenv("AUDD_API_TOKEN") or os.getenv("AUDD_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("AUDD_API_TOKEN ست نشده")

    # multipart ساده
    boundary = "----alimj3AudDBoundary"
    parts: list[bytes] = []

    def add_field(name: str, value: str) -> None:
        parts.append(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                f"{value}\r\n"
            ).encode("utf-8")
        )

    add_field("api_token", token)
    add_field("return", "apple_music,spotify")
    # فایل
    parts.append(
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: {mime or 'application/octet-stream'}\r\n\r\n"
        ).encode("utf-8")
    )
    parts.append(audio_bytes)
    parts.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
    body = b"".join(parts)

    req = urllib.request.Request(
        "https://api.audd.io/",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "User-Agent": "alimj3-bot/1.0"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        data = json.loads(resp.read().decode("utf-8", errors="replace"))

    if str(data.get("status") or "").lower() != "success":
        logger.warning("audd non-success: %s", str(data)[:300])
        return None
    result = data.get("result")
    if not result or not isinstance(result, dict):
        return None
    artist = (result.get("artist") or "").strip()
    title = (result.get("title") or "").strip()
    if not artist and not title:
        return None
    return {
        "artist": artist,
        "title": title,
        "album": (result.get("album") or "").strip(),
        "song_link": (result.get("song_link") or "").strip(),
        "raw": result,
    }


def fetch_lyrics_lrclib(artist: str, title: str) -> Optional[str]:
    """متن از LRCLIB — رایگان، بدون کلید."""
    try:
        q = urllib.parse.urlencode({"q": f"{artist} {title}".strip()})
        search = _http_json(f"https://lrclib.net/api/search?{q}", timeout=20)
        if not isinstance(search, list) or not search:
            # fallback get
            params = urllib.parse.urlencode(
                {"artist_name": artist, "track_name": title}
            )
            item = _http_json(f"https://lrclib.net/api/get?{params}", timeout=20)
            plain = (item.get("plainLyrics") or item.get("syncedLyrics") or "").strip()
            return plain or None

        best = search[0]
        plain = (best.get("plainLyrics") or "").strip()
        if plain:
            return plain
        # گاهی فقط id دارد
        tid = best.get("id")
        if tid:
            item = _http_json(f"https://lrclib.net/api/get/{tid}", timeout=20)
            plain = (item.get("plainLyrics") or item.get("syncedLyrics") or "").strip()
            return plain or None
    except Exception as exc:
        logger.warning("lrclib failed: %s", exc)
    return None


def fetch_lyrics_genius(artist: str, title: str) -> Optional[str]:
    """اختیاری — اگر GENIUS_ACCESS_TOKEN باشد."""
    token = (os.getenv("GENIUS_ACCESS_TOKEN") or "").strip()
    if not token:
        return None
    try:
        q = urllib.parse.urlencode({"q": f"{artist} {title}"})
        req = urllib.request.Request(
            f"https://api.genius.com/search?{q}",
            headers={"Authorization": f"Bearer {token}", "User-Agent": "alimj3-bot/1.0"},
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        hits = ((data.get("response") or {}).get("hits")) or []
        if not hits:
            return None
        # Genius API متن کامل نمی‌دهد بدون scrape — فقط لینک
        url = (hits[0].get("result") or {}).get("url") or ""
        if url:
            return f"(متن کامل در Genius)\n{url}"
    except Exception as exc:
        logger.warning("genius failed: %s", exc)
    return None


def identify_and_lyrics(audio_bytes: bytes, *, filename: str = "voice.ogg", mime: str = "audio/ogg", want_lyrics: bool = True) -> str:
    """خروجی آماده برای ارسال در تلگرام."""
    info = recognize_audd(audio_bytes, filename=filename, mime=mime)
    if not info:
        return (
            "🎵 آهنگ در پایگاه شناسایی پیدا نشد.\n"
            "اگر آهنگ کمتر معروف/جدید است یا کیفیت ویس پایین است، ممکن است شناسایی نشود."
        )

    artist = info["artist"]
    title = info["title"]
    album = info.get("album") or ""
    link = info.get("song_link") or ""

    lines = [
        "🎵 آهنگ شناسایی شد",
        "────────────",
        f"🎤 {artist}",
        f"🎧 {title}",
    ]
    if album:
        lines.append(f"💿 {album}")
    if link:
        lines.append(f"🔗 {link}")

    if want_lyrics:
        lyrics = fetch_lyrics_lrclib(artist, title)
        if not lyrics:
            lyrics = fetch_lyrics_genius(artist, title)
        if lyrics:
            # محدودیت طول تلگرام
            body = lyrics.strip()
            if len(body) > 2800:
                body = body[:2800] + "\n…"
            lines.append("────────────")
            lines.append("📝 متن:")
            lines.append(body)
        else:
            lines.append("────────────")
            lines.append("📝 متن ترانه در منابع آزاد پیدا نشد.")

    return "\n".join(lines)


def wants_music_id(text: str) -> bool:
    t = (text or "").strip()
    return bool(
        re.search(
            r"(?:چه\s*آهنگ|اسم\s*آهنگ|این\s*آهنگ|آهنگ\s*چیه|شناسایی\s*آهنگ|"
            r"ترانه|متن\s*آهنگ|lyrics|lyric|shazam|چه\s*تصنیف)",
            t,
            re.I,
        )
    )


def wants_lyrics(text: str) -> bool:
    t = (text or "").strip()
    return bool(re.search(r"(?:متن|ترانه|lyrics|lyric)", t, re.I))
