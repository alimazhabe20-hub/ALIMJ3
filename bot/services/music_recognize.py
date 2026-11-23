"""شناسایی آهنگ از صدا + دریافت lyrics / زیرنویس.

جریان شناسایی از صدا:
  1) AudD  → artist / title
  2) LRCLIB → متن ترانه
  3) lyrics.ovh → متن
  4) Genius (اگر GENIUS_ACCESS_TOKEN باشد)

جریان متنی:
  - «زیرنویس / متن آهنگ Isabel LaRosa I'm Yours»
  - ریپلای به ویس: «زیرنویسش» / «متن آهنگ بالایی»

Env:
  AUDD_API_TOKEN
  GENIUS_ACCESS_TOKEN  (اختیاری)
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.parse
import urllib.request
from typing import Optional

from bot.logger import logger

# آخرین آهنگ شناسایی‌شده در هر چت (برای «زیرنویسش» / «متن بالایی»)
_LAST_SONG: dict[int, tuple[float, dict]] = {}
_LAST_SONG_TTL = 30 * 60  # 30 دقیقه

# کش کوتاه متن انگلیسی برای دکمه «ترجمه فارسی»
_LYRICS_CACHE: dict[str, tuple[float, str, str]] = {}
_LYRICS_CACHE_TTL = 45 * 60


def store_lyrics_for_translate(card_text: str, lyrics_en: str, *, header: str = "") -> str:
    """ذخیره هدر + lyrics کامل برای دکمه ترجمه. برمی‌گرداند key."""
    import hashlib
    body = (lyrics_en or "").strip()
    if not body or len(body) < 15:
        return ""
    key = hashlib.sha1(f"{card_text[:200]}|{body[:160]}".encode("utf-8")).hexdigest()[:12]
    _LYRICS_CACHE[key] = {
        "ts": time.time(),
        "card": str(card_text or ""),
        "header": str(header or ""),
        "lyrics": body,
        "msg_ids": [],
        "chat_id": None,
    }
    if len(_LYRICS_CACHE) > 2000:
        cutoff = time.time() - _LYRICS_CACHE_TTL
        for k, v in list(_LYRICS_CACHE.items()):
            if isinstance(v, dict) and v.get("ts", 0) < cutoff:
                _LYRICS_CACHE.pop(k, None)
            elif isinstance(v, tuple) and v[0] < cutoff:
                _LYRICS_CACHE.pop(k, None)
    return key


def bind_lyrics_messages(key: str, chat_id: int, message_ids: list[int]) -> None:
    item = _LYRICS_CACHE.get(str(key or ""))
    if not isinstance(item, dict):
        return
    item["chat_id"] = int(chat_id) if chat_id else None
    item["msg_ids"] = [int(x) for x in (message_ids or []) if x]
    _LYRICS_CACHE[str(key)] = item


def pop_lyrics_for_translate(key: str) -> dict | None:
    """dict با keys: header, lyrics, card, msg_ids, chat_id"""
    item = _LYRICS_CACHE.get(str(key or ""))
    if not item:
        return None
    # سازگاری با فرمت قدیمی tuple
    if isinstance(item, tuple):
        ts, card, ly = item
        if time.time() - ts > _LYRICS_CACHE_TTL:
            _LYRICS_CACHE.pop(str(key), None)
            return None
        return {"header": "", "lyrics": ly, "card": card, "msg_ids": [], "chat_id": None}
    if not isinstance(item, dict):
        return None
    if time.time() - float(item.get("ts") or 0) > _LYRICS_CACHE_TTL:
        _LYRICS_CACHE.pop(str(key), None)
        return None
    return item


def split_telegram_messages(header: str, lyrics: str, *, limit: int = 3900) -> list[str]:
    """تقسیم به چند پیام تلگرام؛ هدر فقط روی پیام اول."""
    header = (header or "").rstrip()
    lyrics = (lyrics or "").strip()
    if not lyrics:
        return [header[:limit]] if header else []
    first_budget = limit - len(header) - 40
    if first_budget < 200:
        # هدر جدا، lyrics جدا
        parts = []
        if header:
            parts.append(header[:limit])
        chunks = _chunk_text(lyrics, limit)
        parts.extend(chunks)
        return parts
    # lyrics روی چند پیام؛ اول با هدر
    if len(header) + 2 + len(lyrics) <= limit:
        return [header + "\n────────────\n📝 متن / زیرنویس:\n" + lyrics]
    chunks = _chunk_text(lyrics, max(500, first_budget))
    out = [header + "\n────────────\n📝 متن / زیرنویس:\n" + chunks[0]]
    for c in chunks[1:]:
        out.append("📝 ادامه متن:\n" + c)
    return out


def _chunk_text(text: str, limit: int) -> list[str]:
    text = text.strip()
    if len(text) <= limit:
        return [text]
    lines = text.splitlines(keepends=True)
    chunks, buf = [], ""
    for ln in lines:
        if len(buf) + len(ln) <= limit:
            buf += ln
        else:
            if buf.strip():
                chunks.append(buf.rstrip())
            if len(ln) > limit:
                # خط خیلی بلند
                s = ln
                while len(s) > limit:
                    chunks.append(s[:limit])
                    s = s[limit:]
                buf = s
            else:
                buf = ln
    if buf.strip():
        chunks.append(buf.rstrip())
    return chunks or [text[:limit]]




def remember_song(chat_id: int, meta: dict) -> None:
    try:
        _LAST_SONG[int(chat_id)] = (time.time(), dict(meta or {}))
        if len(_LAST_SONG) > 3000:
            cutoff = time.time() - _LAST_SONG_TTL
            for k, (ts, _) in list(_LAST_SONG.items()):
                if ts < cutoff:
                    _LAST_SONG.pop(k, None)
    except Exception:
        pass


def get_last_song(chat_id: int) -> Optional[dict]:
    item = _LAST_SONG.get(int(chat_id or 0))
    if not item:
        return None
    ts, meta = item
    if time.time() - ts > _LAST_SONG_TTL:
        _LAST_SONG.pop(int(chat_id), None)
        return None
    return meta


def _http_json(
    url: str,
    *,
    data: bytes | None = None,
    headers: dict | None = None,
    method: str = "GET",
    timeout: int = 30,
) -> dict:
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw) if raw else {}


def _http_text(url: str, *, timeout: int = 25) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "alimj3-bot/1.0", "Accept": "application/json,text/plain"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def recognize_audd(
    audio_bytes: bytes, *, filename: str = "voice.ogg", mime: str = "audio/ogg"
) -> Optional[dict]:
    """شناسایی با AudD. خروجی: {artist, title, album, song_link, release_date, label, timecode}."""
    token = (os.getenv("AUDD_API_TOKEN") or os.getenv("AUDD_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("AUDD_API_TOKEN ست نشده")

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
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "alimj3-bot/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        data = json.loads(resp.read().decode("utf-8", errors="replace"))

    if str(data.get("status") or "").lower() != "success":
        logger.warning("audd non-success: %s", str(data)[:300])
        return None
    result = data.get("result")
    if not isinstance(result, dict):
        return None
    artist = str(result.get("artist") or "").strip()
    title = str(result.get("title") or "").strip()
    if not artist and not title:
        return None
    return {
        "artist": artist,
        "title": title,
        "album": str(result.get("album") or "").strip(),
        "song_link": str(result.get("song_link") or "").strip(),
        "release_date": str(result.get("release_date") or "").strip(),
        "label": str(result.get("label") or "").strip(),
        "timecode": str(result.get("timecode") or "").strip(),
    }


def _artist_close(a: str, b: str) -> bool:
    """تشخیص شباهت ساده نام هنرمند."""
    def norm(x: str) -> str:
        x = (x or "").lower()
        x = re.sub(r"[^a-z0-9\u0600-\u06ff\s]", " ", x)
        x = re.sub(r"\s+", " ", x).strip()
        return x
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return True  # اگر یکی خالی است سخت نگیر
    if na == nb or na in nb or nb in na:
        return True
    # overlap کلمات
    wa, wb = set(na.split()), set(nb.split())
    if not wa or not wb:
        return True
    return len(wa & wb) / max(1, min(len(wa), len(wb))) >= 0.5


def fetch_lyrics_lrclib(artist: str, title: str) -> Optional[str]:
    try:
        # اول get دقیق با artist+title
        if artist and title:
            params = urllib.parse.urlencode(
                {"artist_name": artist, "track_name": title}
            )
            try:
                item = _http_json(f"https://lrclib.net/api/get?{params}", timeout=20)
                if isinstance(item, dict):
                    body = item.get("plainLyrics") or item.get("syncedLyrics") or ""
                    if str(body).strip():
                        return str(body).strip()
            except Exception:
                pass

        q = urllib.parse.urlencode({"q": f"{artist} {title}".strip()})
        search = _http_json(f"https://lrclib.net/api/search?{q}", timeout=20)
        if not isinstance(search, list) or not search:
            return None

        # ترجیح نتیجه با هنرمند هم‌خوان
        ranked = []
        for item in search:
            if not isinstance(item, dict):
                continue
            a = str(item.get("artistName") or item.get("artist_name") or "")
            score = 2 if _artist_close(artist, a) else 0
            if str(item.get("trackName") or item.get("name") or "").lower().find(
                (title or "").lower()[:12]
            ) >= 0:
                score += 1
            ranked.append((score, item))
        ranked.sort(key=lambda x: -x[0])
        for score, best in ranked:
            if artist and score < 2:
                # هنرمند مشخص بوده ولی هیچ نتیجه‌ای match نکرد
                continue
            body = best.get("plainLyrics") or best.get("syncedLyrics")
            if body and str(body).strip():
                return str(body).strip()
            tid = best.get("id")
            if tid:
                item = _http_json(f"https://lrclib.net/api/get/{tid}", timeout=20)
                if isinstance(item, dict):
                    body = item.get("plainLyrics") or item.get("syncedLyrics") or ""
                    if str(body).strip():
                        return str(body).strip()
        # بدون تطبیق هنرمند → متن برنگردان (جلوگیری از lyrics اشتباه مثل Mraz روی Saur)
        if artist and ranked and ranked[0][0] < 2:
            logger.info(
                "lrclib skip mismatched artist audd=%r best=%r",
                artist,
                (ranked[0][1].get("artistName") if ranked else None),
            )
            return None
    except Exception as exp:
        logger.warning("lrclib failed: %s", exp)
    return None


def fetch_lyrics_ovh(artist: str, title: str) -> Optional[str]:
    """lyrics.ovh — رایگان، بدون کلید."""
    try:
        a = urllib.parse.quote(artist.strip())
        t = urllib.parse.quote(title.strip())
        raw = _http_text(f"https://api.lyrics.ovh/v1/{a}/{t}", timeout=20)
        data = json.loads(raw) if raw else {}
        body = str(data.get("lyrics") or "").strip()
        if body and len(body) > 20:
            # حذف هدر رایج
            body = re.sub(r"^Paroles de la chanson.*?\n+", "", body, flags=re.I)
            return body.strip() or None
    except Exception as exc:
        logger.warning("lyrics.ovh failed: %s", exc)
    return None


def fetch_lyrics_genius(artist: str, title: str) -> Optional[str]:
    token = (os.getenv("GENIUS_ACCESS_TOKEN") or os.getenv("GENIUS_TOKEN") or "").strip()
    if not token:
        return None
    try:
        q = urllib.parse.urlencode({"q": f"{artist} {title}".strip()})
        data = _http_json(
            f"https://api.genius.com/search?{q}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )
        hits = (data.get("response") or {}).get("hits") or []
        if not hits:
            return None
        # Genius API متن کامل نمی‌دهد؛ فقط لینک — برای متن کامل به scrape نیاز است
        # اینجا فقط اگر preview در نتیجه باشد
        for h in hits[:3]:
            res = (h or {}).get("result") or {}
            url = res.get("url") or ""
            if url:
                # بدون scrape فقط لینک را به‌عنوان راهنما برمی‌گردانیم نه lyrics
                logger.info("genius hit: %s", url)
                break
        return None
    except Exception as exc:
        logger.warning("genius failed: %s", exc)
    return None


def fetch_lyrics(artist: str, title: str) -> Optional[str]:
    artist = (artist or "").strip()
    title = (title or "").strip()
    if not title:
        return None
    lyrics = fetch_lyrics_lrclib(artist, title)
    if lyrics:
        return lyrics
    if artist:
        lyrics = fetch_lyrics_ovh(artist, title)
        if lyrics:
            return lyrics
    # بدون هنرمند فقط اگر عنوان خیلی خاص باشد (نه I'm Yours و مشابه)
    common = {
        "i'm yours", "im yours", "i am yours", "hello", "stay", "sorry",
        "perfect", "someone like you", "shape of you", "believer",
    }
    if not artist and title.lower().strip() not in common:
        lyrics = fetch_lyrics_lrclib("", title)
        if lyrics:
            return lyrics
        lyrics = fetch_lyrics_ovh("", title)
        if lyrics:
            return lyrics
    fetch_lyrics_genius(artist, title)
    return None


def _norm_fa_music(text: str) -> str:
    t = str(text or "").strip().replace("ي", "ی").replace("ك", "ک")
    t = t.replace("اهنگ", "آهنگ")
    t = t.replace("زیر نویس", "زیرنویس")
    t = t.replace("زیر‌نویس", "زیرنویس")
    return t


def wants_music_id(text: str) -> bool:
    t = _norm_fa_music(text)
    if re.fullmatch(r"آهنگ|music|song|shazam", t, re.I):
        return True
    return bool(
        re.search(
            r"(?:چه\s*آهنگ|اسم\s*آهنگ|این\s*آهنگ|آهنگ\s*چیه|شناسایی\s*آهنگ|"
            r"آهنگ|ترانه|شازم|shazam|چه\s*تصنیف)",
            t,
            re.I,
        )
    )


def wants_lyrics(text: str) -> bool:
    t = _norm_fa_music(text)
    return bool(
        re.search(
            r"(?:"
            r"متن\s*آهنگ|متن\s*ترانه|ترانه|"
            r"زیرنویس|زیر\s*نویس|subtitle|captions?|"
            r"lyrics|lyric|"
            r"متنشو|متن\s*شو|زیرنویسشو|زیرنویسش|"
            r"lyric\s*این|متن\s*این\s*آهنگ"
            r")",
            t,
            re.I,
        )
    )


def wants_previous_lyrics(text: str) -> bool:
    """درخواست متن/زیرنویس برای آهنگ قبلی یا پیام بالایی."""
    t = _norm_fa_music(text)
    return bool(
        re.search(
            r"(?:"
            r"زیرنویس(?:ش|شو)?|"
            r"متن(?:ش|شو)?|"
            r"(?:آهنگ|ویس|صدا|پیام)\s*(?:بالا|قبلی|همین)|"
            r"بالایی|قبلی"
            r").*"
            r"(?:آهنگ|ترانه|زیرنویس|متن|lyric)|"
            r"(?:متن|زیرنویس|lyric).*"
            r"(?:بالا|قبلی|همین|آهنگ)"
            r")",
            t,
            re.I,
        )
    ) or (
        wants_lyrics(t)
        and bool(re.search(r"بالا|قبلی|همین|شو\b|ش\b", t, re.I))
    )


def parse_artist_title(text: str) -> Optional[tuple[str, str]]:
    """استخراج (artist, title) از متن کاربر."""
    t = _norm_fa_music(text)
    t = re.sub(
        r"(?:ربات|بات|لطفاً|لطفا|میخوام|می‌خوام|بده|بفرست|پیدا\s*کن)",
        " ",
        t,
        flags=re.I,
    )
    t = re.sub(
        r"(?:متن|زیرنویس|lyrics|lyric|آهنگ|ترانه)\s*",
        " ",
        t,
        flags=re.I,
    )
    t = re.sub(r"\s+", " ", t).strip(" :-–—|")

    # خواننده X آهنگ Y
    m = re.search(
        r"(?:خواننده|خواننده‌اش|artist|singer)\s*[:\-]?\s*(.+?)\s+"
        r"(?:آهنگ|ترانه|عنوان|title|song)\s*[:\-]?\s*(.+)$",
        t,
        re.I,
    )
    if m:
        return m.group(1).strip(' :-'), m.group(2).strip(' :-')

    # X - Y  یا  X – Y
    m = re.search(r"^(.{2,40}?)\s*[-–—]\s*(.{2,60})$", t)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    # by Artist
    m = re.search(r"^(.+?)\s+by\s+(.+)$", t, re.I)
    if m:
        return m.group(2).strip(), m.group(1).strip()

    # فقط عنوان اگر کوتاه است
    if 2 <= len(t) <= 60 and not re.search(r"[؟?]", t):
        # بدون artist
        return "", t
    return None



def _common_title_warning(artist: str, title: str) -> str:
    t = (title or "").lower().strip()
    common = {"i'm yours", "im yours", "i am yours", "hello", "stay", "sorry", "perfect"}
    if t in common:
        return (
            "\n⚠️ عنوان پرتکرار است؛ ممکن است AudD نسخه/کاور دیگری را گرفته باشد.\n"
            "اگر خواننده اشتباه است بنویس: خواننده … آهنگ …"
        )
    return ""

def format_song_card(meta: dict, lyrics: Optional[str] = None) -> str:
    artist = str(meta.get("artist") or "—")
    title = str(meta.get("title") or "—")
    lines = [
        "🎵 آهنگ شناسایی شد",
        "────────────",
        f"🎤 هنرمند: {artist}",
        f"🎧 عنوان: {title}",
    ]
    if meta.get("album"):
        lines.append(f"💿 آلبوم: {meta['album']}")
    if meta.get("release_date"):
        lines.append(f"📅 انتشار: {meta['release_date']}")
    if meta.get("label"):
        lines.append(f"🏷 ناشر: {meta['label']}")
    if meta.get("timecode"):
        lines.append(f"📊 تطبیق: {meta['timecode']}")
    lines.append("────────────")
    if meta.get("song_link"):
        lines.append(f"🔗 {meta['song_link']}")
    if meta.get("source"):
        lines.append(f"🛠 منبع: {meta['source']}")
    else:
        lines.append("🛠 منبع شناسایی: AudD")
    # اگر خودمان عنوان را اصلاح کردیم، هشدار گمراه‌کننده نشان نده
    if not meta.get("_corrected"):
        warn = _common_title_warning(artist, title)
        if warn:
            lines.append(warn)
    if lyrics:
        body = lyrics.strip()
        lines.append("────────────")
        lines.append("📝 متن / زیرنویس:")
        lines.append(body)
    else:
        lines.append("────────────")
        lines.append("📝 متن مطمئن برای این هنرمند+عنوان پیدا نشد.")
        lines.append(
            "اگر خواننده اشتباه است (رایج برای عنوان‌های پرتکرار)، بنویس:\n"
            "خواننده Jason Mraz آهنگ I'm Yours\n"
            "یا: خواننده Isabel LaRosa آهنگ I'm Yours"
        )
    return "\n".join(lines)



def _distinctive_snippets(transcript: str) -> list[str]:
    """عبارات متمایز از STT برای جستجوی lyrics (نه کلمات خیلی عمومی)."""
    t = re.sub(r"\s+", " ", str(transcript or "")).strip()
    if len(t) < 12:
        return []
    # جملات
    parts = re.split(r"[.!?,\n]| و ", t)
    out = []
    skip = {
        "baby", "love", "yeah", "oh", "i", "you", "the", "a", "and", "to", "me",
        "my", "it", "is", "in", "on", "of", "lost", "more", "need",
    }
    for p in parts:
        p = p.strip()
        words = [w for w in re.findall(r"[A-Za-z\u0600-\u06FF']+", p) if len(w) > 1]
        if len(words) < 3:
            continue
        low = {w.lower() for w in words}
        if len(low - skip) < 2:
            continue
        if 12 <= len(p) <= 80:
            out.append(p)
    # کل متن کوتاه
    if 20 <= len(t) <= 120 and t not in out:
        out.insert(0, t[:120])
    return out[:5]


def _lyrics_overlap_score(lyrics: str, transcript: str) -> float:
    """چند درصد کلمات معنادار transcript در lyrics هست."""
    def tokens(s: str) -> set[str]:
        words = re.findall(r"[a-zA-Z']{3,}", (s or "").lower())
        stop = {
            "the", "and", "you", "for", "that", "this", "with", "have", "was",
            "are", "but", "not", "your", "from", "they", "been", "has", "had",
            "baby", "love", "yeah", "dont", "it's", "im", "youre",
        }
        return {w for w in words if w not in stop}
    a, b = tokens(transcript), tokens(lyrics)
    if not a or not b:
        return 0.0
    return len(a & b) / max(1, len(a))


def search_by_lyrics_snippet(snippet: str) -> Optional[dict]:
    """جستجوی آهنگ از روی تکه‌متن (STT) در LRCLIB."""
    sn = re.sub(r"\s+", " ", str(snippet or "")).strip()
    if len(sn) < 10:
        return None
    try:
        q = urllib.parse.urlencode({"q": sn[:80]})
        search = _http_json(f"https://lrclib.net/api/search?{q}", timeout=20)
        if not isinstance(search, list) or not search:
            return None
        best = None
        best_score = 0.0
        for item in search[:8]:
            if not isinstance(item, dict):
                continue
            body = str(item.get("plainLyrics") or item.get("syncedLyrics") or "")
            score = _lyrics_overlap_score(body, sn) if body else 0.0
            # عنوان/هنرمند در query
            title = str(item.get("trackName") or item.get("name") or "")
            artist = str(item.get("artistName") or item.get("artist_name") or "")
            if not body and title:
                # get full
                tid = item.get("id")
                if tid:
                    try:
                        full = _http_json(f"https://lrclib.net/api/get/{tid}", timeout=15)
                        if isinstance(full, dict):
                            body = str(full.get("plainLyrics") or full.get("syncedLyrics") or "")
                            score = _lyrics_overlap_score(body, sn)
                    except Exception:
                        pass
            if score > best_score and artist and title:
                best_score = score
                best = {
                    "artist": artist,
                    "title": title,
                    "album": str(item.get("albumName") or item.get("album_name") or ""),
                    "lyrics": body.strip() if body else None,
                    "source": "LRCLIB/snippet",
                    "_score": score,
                }
        if best and best_score >= 0.25:
            return best
    except Exception as exc:
        logger.warning("snippet search failed: %s", exc)
    return None



# وقتی AudD کاور اشتباه می‌دهد، برای عنوان‌های معروف جایگزین‌های محتمل
_COMMON_TITLE_ALTERNATES: dict[str, list[tuple[str, str]]] = {
    "i'm yours": [
        ("Isabel LaRosa", "I'm Yours"),
        ("Jason Mraz", "I'm Yours"),
    ],
    "im yours": [
        ("Isabel LaRosa", "I'm Yours"),
        ("Jason Mraz", "I'm Yours"),
    ],
    "i am yours": [
        ("Isabel LaRosa", "I'm Yours"),
        ("Jason Mraz", "I'm Yours"),
    ],
}


def resolve_song_meta(
    audd: Optional[dict],
    *,
    transcript_hint: str = "",
    want_lyrics: bool = True,
) -> tuple[Optional[dict], Optional[str]]:
    """ادغام AudD + تأیید با متن ویس + جایگزین عنوان‌های پرتکرار."""
    transcript_hint = str(transcript_hint or "").strip()
    info = dict(audd) if audd else None
    lyrics = None

    if info and want_lyrics:
        lyrics = fetch_lyrics(info.get("artist") or "", info.get("title") or "")

    title_l = (info.get("title") or "").lower().strip() if info else ""
    artist_l = (info.get("artist") or "").lower().strip() if info else ""

    # --- تأیید / اصلاح با STT ---
    if transcript_hint and len(transcript_hint) >= 12:
        overlap = _lyrics_overlap_score(lyrics or "", transcript_hint) if lyrics else 0.0
        need_snippet = (not info) or (not lyrics) or (overlap < 0.2)
        if title_l in _COMMON_TITLE_ALTERNATES and overlap < 0.35:
            need_snippet = True

        if need_snippet:
            for sn in _distinctive_snippets(transcript_hint):
                hit = search_by_lyrics_snippet(sn)
                if not hit:
                    continue
                if (hit.get("_score") or 0) >= 0.22:
                    info = {
                        "artist": hit["artist"],
                        "title": hit["title"],
                        "album": hit.get("album") or "",
                        "song_link": (info or {}).get("song_link") or "",
                        "source": hit.get("source") or "LRCLIB/snippet",
                    }
                    lyrics = hit.get("lyrics") or fetch_lyrics(
                        hit["artist"], hit["title"]
                    )
                    title_l = (info.get("title") or "").lower().strip()
                    artist_l = (info.get("artist") or "").lower().strip()
                    logger.info(
                        "song corrected via snippet -> %s - %s (score=%.2f)",
                        info["artist"],
                        info["title"],
                        hit.get("_score") or 0,
                    )
                    break

            # نشانه‌های قوی Isabel LaRosa - I'm Yours
            if re.search(
                r"pretty\s*,?\s*it\s*hurts|trip\s*over\s*my\s*words|"
                r"view\s*of\s*your\s*headlights|pray\s*to\s*the\s*lord",
                transcript_hint,
                re.I,
            ):
                info = {
                    "artist": "Isabel LaRosa",
                    "title": "I'm Yours",
                    "album": "I'm Yours",
                    "song_link": (info or {}).get("song_link") or "",
                    "source": "تطبیق متن ویس",
                }
                lyrics = fetch_lyrics("Isabel LaRosa", "I'm Yours") or lyrics
                logger.info("song forced Isabel LaRosa via transcript markers")

    # --- بدون STT: عنوان پرتکرار + lyrics ناموفق برای هنرمند AudD ---
    if info and want_lyrics and title_l in _COMMON_TITLE_ALTERNATES:
        need_alt = not lyrics
        # اگر lyrics آمده ولی هنرمند AudD جزو جایگزین‌ها نیست، مشکوک است
        alts = _COMMON_TITLE_ALTERNATES[title_l]
        alt_artists = {a.lower() for a, _ in alts}
        if artist_l and artist_l not in alt_artists and not lyrics:
            need_alt = True
        if artist_l and artist_l not in alt_artists and lyrics:
            # lyrics ممکن است مال هنرمند دیگری باشد که با عنوان match شده
            need_alt = True
            lyrics = None

        if need_alt:
            for alt_artist, alt_title in alts:
                if artist_l and artist_l == alt_artist.lower():
                    continue
                ly = fetch_lyrics(alt_artist, alt_title)
                if ly and len(ly) > 40:
                    info = {
                        "artist": alt_artist,
                        "title": alt_title,
                        "album": alt_title,
                        "song_link": "",
                        "release_date": "",
                        "label": "",
                        "timecode": "",
                        "source": f"AudD+اصلاح عنوان ({alt_artist})",
                        "_corrected": True,
                    }
                    lyrics = ly
                    logger.info(
                        "common-title alternate applied: %s - %s (was %s)",
                        alt_artist,
                        alt_title,
                        artist_l,
                    )
                    break

    return info, lyrics



def identify_and_lyrics(
    audio_bytes: bytes,
    *,
    filename: str = "voice.ogg",
    mime: str = "audio/ogg",
    want_lyrics: bool = True,
    chat_id: int | None = None,
    transcript_hint: str = "",
) -> str:
    try:
        audd = recognize_audd(audio_bytes, filename=filename, mime=mime)
    except Exception as exc:
        logger.warning("audd error: %s", exc)
        audd = None

    info, lyrics = resolve_song_meta(
        audd, transcript_hint=transcript_hint, want_lyrics=want_lyrics
    )

    if not info:
        # آخرین شانس: فقط snippet
        if transcript_hint:
            for sn in _distinctive_snippets(transcript_hint):
                hit = search_by_lyrics_snippet(sn)
                if hit:
                    info = {
                        "artist": hit["artist"],
                        "title": hit["title"],
                        "album": hit.get("album") or "",
                        "source": hit.get("source") or "LRCLIB/snippet",
                    }
                    lyrics = hit.get("lyrics")
                    break
        if not info:
            return (
                "🎵 آهنگ در پایگاه شناسایی پیدا نشد.\n"
                "اگر آهنگ کمتر معروف/جدید است یا کیفیت ویس پایین است، ممکن است شناسایی نشود.\n"
                "نام خواننده و عنوان را تایپ کن تا متن/زیرنویس را پیدا کنم.\n"
                "مثال: خواننده Isabel LaRosa آهنگ I'm Yours"
            )

    if not info.get("source"):
        info["source"] = "AudD"
    if chat_id:
        remember_song(chat_id, info)
    if want_lyrics and not lyrics:
        lyrics = fetch_lyrics(info.get("artist") or "", info.get("title") or "")
    return format_song_card(info, lyrics if want_lyrics else None)



def lyrics_for_query(text: str, *, chat_id: int | None = None) -> Optional[str]:
    """جستجوی متن با نام خواننده/آهنگ یا آخرین آهنگ چت."""
    t = _norm_fa_music(text)

    # اول: artist/title در متن
    parsed = parse_artist_title(t)
    if parsed:
        artist, title = parsed
        if title:
            lyrics = fetch_lyrics(artist, title)
            meta = {
                "artist": artist or "—",
                "title": title,
                "source": "جستجوی متنی",
            }
            if chat_id:
                remember_song(chat_id, meta)
            return format_song_card(meta, lyrics)

    # دوم: آخرین آهنگ همین چت
    if chat_id and wants_lyrics(t):
        last = get_last_song(chat_id)
        if last and last.get("title"):
            lyrics = fetch_lyrics(last.get("artist") or "", last.get("title") or "")
            return format_song_card(last, lyrics)

    return None


def extract_lyrics_block(message_text: str) -> str:
    """استخراج بخش متن ترانه از خروجی identify_and_lyrics / format_song_card."""
    s = str(message_text or "")
    m = re.search(
        r"(?:📝\s*متن(?:\s*/\s*زیرنویس)?\s*:?\s*)([\s\S]+)$",
        s,
    )
    if m:
        body = m.group(1).strip()
        if "پیدا نشد" in body:
            return ""
        return body
    return ""
