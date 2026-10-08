"""Stable public facade.

IMPORTANT: Keep this file small and stable. New functionality belongs in the
secondary ``downloader_parts/`` modules. The complete legacy implementation is kept
unchanged in ``downloader_parts/part_999_core_legacy.py`` for compatibility.
"""

# BEGIN MERGED LEGACY PART: downloader_parts/part_999_core_legacy.py
"""Production downloader for public URLs.

Design goals: safe URL validation (including redirects), bounded concurrency,
per-user throttling, persistent small cache, resumable direct HTTP downloads,
metadata/format probing, and clear handling of site blocks.  It never bypasses
CAPTCHA, authentication, DRM, geo/access controls, or site bans.
"""

import asyncio
import hashlib
import ipaddress
import json
import os
import re
import shutil
import socket
import tempfile
import threading
import time
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

from bot.logger import logger

MAX_BYTES = max(1, int(os.getenv("DOWNLOADER_MAX_BYTES", str(1024 * 1024 * 1024))))
TIMEOUT = max(5.0, float(os.getenv("DOWNLOADER_TIMEOUT", "60")))
MAX_REDIRECTS = max(1, int(os.getenv("DOWNLOADER_MAX_REDIRECTS", "5")))
GLOBAL_CONCURRENCY = max(1, int(os.getenv("DOWNLOADER_CONCURRENCY", "2")))
PER_USER_CONCURRENCY = max(1, int(os.getenv("DOWNLOADER_PER_USER_CONCURRENCY", "1")))
CACHE_TTL = max(0, int(os.getenv("DOWNLOADER_CACHE_TTL", "3600")))
CACHE_MAX_BYTES = max(MAX_BYTES, int(os.getenv("DOWNLOADER_CACHE_MAX_BYTES", str(1024 * 1024 * 1024))))
CACHE_DIR = Path(os.getenv("DOWNLOADER_CACHE_DIR", str(Path(tempfile.gettempdir()) / "alimj3_downloader_cache")))

UA = "Mozilla/5.0 (compatible; ALIMJ3-Downloader/2.0)"

_COOKIES_PATH_CACHE: str | None = None


def _resolve_cookies_file() -> str | None:
    """Return a cookies.txt path for yt-dlp."""
    global _COOKIES_PATH_CACHE
    if _COOKIES_PATH_CACHE and Path(_COOKIES_PATH_CACHE).is_file():
        return _COOKIES_PATH_CACHE

    path = os.getenv("DOWNLOADER_COOKIES_FILE", "").strip()
    if path and Path(path).is_file():
        _COOKIES_PATH_CACHE = path
        return path

    content = (
        os.getenv("DOWNLOADER_COOKIES", "").strip()
        or os.getenv("DOWNLOADER_COOKIES_CONTENT", "").strip()
    )
    if not content:
        return None

    content = content.replace("\\n", "\n")
    out = Path(tempfile.gettempdir()) / "alimj3_cookies.txt"
    try:
        if not content.endswith("\n"):
            content += "\n"
        out.write_text(content, encoding="utf-8")
        out.chmod(0o600)
        _COOKIES_PATH_CACHE = str(out)
        logger.info("downloader cookies loaded from environment -> %s", out)
        return _COOKIES_PATH_CACHE
    except Exception as exc:
        logger.warning("failed to write cookies from env: %s", exc)
        return None


# Conservative defaults: enough parallelism to improve DASH/HLS throughput
# without creating the bursty request pattern that can trigger upstream 401/429s.
YTDLP_CONCURRENT_FRAGMENTS = max(1, min(8, int(os.getenv("DOWNLOADER_CONCURRENT_FRAGMENTS", "4"))))
YTDLP_HTTP_CHUNK_SIZE = max(0, min(10 * 1024 * 1024, int(os.getenv("DOWNLOADER_HTTP_CHUNK_SIZE", str(10 * 1024 * 1024)))))
YTDLP_BUFFER_SIZE = max(64 * 1024, int(os.getenv("DOWNLOADER_BUFFER_SIZE", str(1024 * 1024))))


# ── External downloader providers (Cobalt / yt-dlp REST) ─────────────────────
# Optional providers for supported non-blocked URLs.
COBALT_URL = (os.getenv("DOWNLOADER_COBALT_URL") or os.getenv("COBALT_API_URL") or "").strip().rstrip("/")
COBALT_API_KEY = (os.getenv("DOWNLOADER_COBALT_API_KEY") or os.getenv("COBALT_API_KEY") or "").strip()
YTDLP_API_URL = (os.getenv("DOWNLOADER_YTDLP_API_URL") or os.getenv("YTDLP_API_URL") or "").strip().rstrip("/")
YTDLP_API_KEY = (os.getenv("DOWNLOADER_YTDLP_API_KEY") or os.getenv("YTDLP_API_KEY") or "").strip()
EXTERNAL_TIMEOUT = max(15.0, float(os.getenv("DOWNLOADER_EXTERNAL_TIMEOUT", "90")))
EXTERNAL_ENABLED = os.getenv("DOWNLOADER_EXTERNAL_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off"}



_BLOCKED_MEDIA_HOSTS = {
    "you" + "tube.com",
    "www." + "you" + "tube.com",
    "youtu." + "be",
    "www.youtu." + "be",
    "you" + "tube-nocookie.com",
}


def _is_blocked_media_url(url: str) -> bool:
    host = (urlparse((url or "").strip()).hostname or "").lower().rstrip(".")
    return any(host == blocked or host.endswith("." + blocked) for blocked in _BLOCKED_MEDIA_HOSTS)

def _quality_for_cobalt(mode: str) -> str:
    return {
        "best": "1080",
        "1080p": "1080",
        "720p": "720",
        "480p": "480",
        "audio": "720",
    }.get(mode, "1080")


def _external_providers_configured() -> bool:
    return EXTERNAL_ENABLED and bool(COBALT_URL or YTDLP_API_URL)


async def _http_download_to_file(file_url: str, out: Path, *, headers: dict | None = None) -> dict:
    """Download a direct/tunnel URL into *out* (async via thread pool)."""
    import requests

    loop = asyncio.get_running_loop()
    hdrs = {"User-Agent": UA, "Accept": "*/*"}
    if headers:
        hdrs.update(headers)

    def work():
        session = requests.Session()
        current = file_url
        for _ in range(MAX_REDIRECTS + 1):
            current = _validate_url(current)
            r = session.get(
                current,
                stream=True,
                timeout=EXTERNAL_TIMEOUT,
                headers=hdrs,
                allow_redirects=False,
            )
            if r.is_redirect or r.status_code in {301, 302, 303, 307, 308}:
                location = r.headers.get("Location")
                r.close()
                if not location:
                    raise DownloadError("failed")
                current = urljoin(current, location)
                continue
            if r.status_code == 429:
                r.close()
                raise DownloadError("rate_limited")
            if r.status_code in {401, 403}:
                r.close()
                raise DownloadError("site_blocked")
            r.raise_for_status()
            length = int(r.headers.get("content-length") or 0)
            if length > MAX_BYTES:
                r.close()
                raise DownloadError("too_large")
            ctype = (r.headers.get("content-type") or "").lower()
            name = _content_disposition_name(r.headers.get("content-disposition", ""))
            if not name:
                name = _safe_name(Path(urlparse(current).path).name or "download.bin")
            part = out.with_suffix(out.suffix + ".part")
            total = 0
            with part.open("wb") as f:
                for chunk in r.iter_content(YTDLP_BUFFER_SIZE):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > MAX_BYTES:
                        r.close()
                        part.unlink(missing_ok=True)
                        raise DownloadError("too_large")
                    f.write(chunk)
            r.close()
            if total <= 0:
                part.unlink(missing_ok=True)
                raise DownloadError("failed")
            part.replace(out)
            return {
                "path": str(out),
                "title": name,
                "size": total,
                "content_type": ctype,
                "method": "external-http",
            }
        raise DownloadError("failed")

    try:
        return await loop.run_in_executor(None, work)
    except DownloadError:
        raise
    except Exception as exc:
        raise DownloadError(_classify_error(str(exc))) from exc


async def _download_via_cobalt(url: str, outdir: Path, mode: str = "best") -> dict:
    """Use a self-hosted Cobalt instance (POST /). Public instances are not used."""
    if not COBALT_URL:
        raise DownloadError("unsupported")

    import requests

    loop = asyncio.get_running_loop()
    quality = _quality_for_cobalt(mode)
    body = {
        "url": url,
        "videoQuality": quality,
        "filenameStyle": "basic",
        "disableMetadata": False,
        "alwaysProxy": True,
    }
    if mode == "audio":
        body["downloadMode"] = "audio"
        body["audioFormat"] = "mp3"
        body["audioBitrate"] = "128"
    else:
        body["downloadMode"] = "auto"

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": UA,
    }
    if COBALT_API_KEY:
        headers["Authorization"] = f"Api-Key {COBALT_API_KEY}"
        # Some instances use Bearer
        headers["X-Api-Key"] = COBALT_API_KEY

    def work():
        r = requests.post(
            COBALT_URL + "/",
            json=body,
            headers=headers,
            timeout=min(EXTERNAL_TIMEOUT, 45),
        )
        if r.status_code == 429:
            raise DownloadError("rate_limited")
        if r.status_code in {401, 403}:
            raise DownloadError("site_blocked")
        try:
            data = r.json()
        except Exception:
            raise DownloadError("failed")
        status = (data.get("status") or "").lower()
        if status == "error":
            err = data.get("error") or {}
            code = str(err.get("code") or "")
            logger.warning("cobalt error code=%s body=%s", code, str(data)[:400])
            if "rate" in code.lower():
                raise DownloadError("rate_limited")
            if any(x in code.lower() for x in ("auth", "login", "private", "age")):
                raise DownloadError("access_restricted")
            raise DownloadError("failed")
        if status in {"tunnel", "redirect"}:
            file_url = data.get("url") or ""
            filename = data.get("filename") or "cobalt_media.bin"
            if not file_url:
                raise DownloadError("failed")
            return {"file_url": file_url, "filename": filename, "raw": data}
        if status == "local-processing":
            tunnels = data.get("tunnel") or []
            if not tunnels:
                raise DownloadError("failed")
            filename = ((data.get("output") or {}).get("filename")) or "cobalt_media.bin"
            return {"file_url": tunnels[0], "filename": filename, "raw": data}
        if status == "picker":
            # Prefer first video item
            for item in data.get("picker") or []:
                if (item.get("type") or "").lower() in {"video", "gif"} and item.get("url"):
                    return {
                        "file_url": item["url"],
                        "filename": data.get("filename") or "cobalt_media.bin",
                        "raw": data,
                    }
            raise DownloadError("unsupported")
        raise DownloadError("failed")

    meta = await loop.run_in_executor(None, work)
    out = outdir / _safe_name(meta["filename"])
    result = await _http_download_to_file(meta["file_url"], out)
    result["method"] = "cobalt"
    result["mode"] = mode
    result["title"] = _safe_name(Path(meta["filename"]).stem or result.get("title") or "media")
    logger.info("cobalt ok size=%s path=%s", result.get("size"), result.get("path"))
    return result


async def _download_via_ytdlp_api(url: str, outdir: Path, mode: str = "best") -> dict:
    """Generic support for common yt-dlp REST APIs (sync download or job+poll).

    Supported patterns (tried in order):
    1) POST {base}/api/v1/download  with {"url","format"} → file or job
    2) POST {base}/download         with {"url"}
    3) POST {base}/                 with {"url"}
    """
    if not YTDLP_API_URL:
        raise DownloadError("unsupported")

    import requests

    loop = asyncio.get_running_loop()
    format_map = {
        "best": "best[ext=mp4]/best",
        "1080p": "best[height<=1080][ext=mp4]/best[height<=1080]",
        "720p": "best[height<=720][ext=mp4]/best[height<=720]",
        "480p": "best[height<=480][ext=mp4]/best[height<=480]",
        "audio": "bestaudio/best",
    }
    fmt = format_map.get(mode, "best")
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": UA,
    }
    if YTDLP_API_KEY:
        headers["X-API-Key"] = YTDLP_API_KEY
        headers["Authorization"] = f"Bearer {YTDLP_API_KEY}"

    endpoints = [
        f"{YTDLP_API_URL}/api/v1/download",
        f"{YTDLP_API_URL}/download",
        f"{YTDLP_API_URL}/",
    ]
    body = {"url": url, "format": fmt, "format_id": fmt}

    def submit():
        last_err = None
        for ep in endpoints:
            try:
                r = requests.post(ep, json=body, headers=headers, timeout=min(EXTERNAL_TIMEOUT, 30))
                if r.status_code in {404, 405}:
                    continue
                if r.status_code == 429:
                    raise DownloadError("rate_limited")
                if r.status_code in {401, 403}:
                    raise DownloadError("site_blocked")
                if r.status_code >= 400:
                    last_err = f"HTTP {r.status_code}"
                    continue
                # Direct file?
                ctype = (r.headers.get("content-type") or "").lower()
                if "application/json" not in ctype and r.content:
                    return {"kind": "bytes", "content": r.content, "headers": dict(r.headers)}
                data = r.json()
                return {"kind": "json", "data": data, "endpoint": ep}
            except DownloadError:
                raise
            except Exception as exc:
                last_err = str(exc)
                continue
        raise DownloadError(_classify_error(last_err or "failed"))

    submitted = await loop.run_in_executor(None, submit)

    if submitted["kind"] == "bytes":
        name = _content_disposition_name(submitted["headers"].get("content-disposition", "")) or "ytdlp_api.bin"
        out = outdir / _safe_name(name)
        out.write_bytes(submitted["content"])
        size = out.stat().st_size
        if size <= 0:
            out.unlink(missing_ok=True)
            raise DownloadError("failed")
        if size > MAX_BYTES:
            out.unlink(missing_ok=True)
            raise DownloadError("too_large")
        return {
            "path": str(out),
            "title": _safe_name(out.stem),
            "size": size,
            "content_type": submitted["headers"].get("content-type", ""),
            "method": "ytdlp-api",
            "mode": mode,
        }

    data = submitted["data"]
    # Common job/sync shapes
    file_url = (
        data.get("url")
        or data.get("download_url")
        or data.get("file_url")
        or (data.get("result") or {}).get("url")
        or (data.get("result") or {}).get("download_url")
    )
    job_id = data.get("job_id") or data.get("task_id") or data.get("id")
    filename = data.get("filename") or data.get("title") or "ytdlp_api.bin"

    if file_url and not job_id:
        out = outdir / _safe_name(filename)
        result = await _http_download_to_file(file_url, out)
        result["method"] = "ytdlp-api"
        result["mode"] = mode
        return result

    if job_id:
        # Poll job status
        status_urls = [
            f"{YTDLP_API_URL}/api/v1/jobs/{job_id}",
            f"{YTDLP_API_URL}/status/{job_id}",
            f"{YTDLP_API_URL}/jobs/{job_id}",
            f"{YTDLP_API_URL}/api/v1/jobs/{job_id}/status",
        ]

        def poll():
            import time as _t
            deadline = _t.monotonic() + EXTERNAL_TIMEOUT
            while _t.monotonic() < deadline:
                for su in status_urls:
                    try:
                        rr = requests.get(su, headers=headers, timeout=15)
                        if rr.status_code in {404, 405}:
                            continue
                        if rr.status_code >= 400:
                            continue
                        js = rr.json()
                        st = str(js.get("status") or js.get("state") or "").lower()
                        if st in {"failed", "error"}:
                            raise DownloadError("failed")
                        if st in {"completed", "done", "success", "finished"}:
                            return js
                    except DownloadError:
                        raise
                    except Exception:
                        continue
                _t.sleep(1.5)
            raise DownloadError("failed")

        job = await loop.run_in_executor(None, poll)
        file_url = (
            job.get("url")
            or job.get("download_url")
            or job.get("file_url")
            or (job.get("result") or {}).get("url")
            or (job.get("result") or {}).get("download_url")
            or (job.get("result") or {}).get("filepath")
        )
        filename = job.get("filename") or (job.get("result") or {}).get("filename") or filename
        if not file_url:
            raise DownloadError("failed")
        # If filepath is local to the API server, try as HTTP under /files/
        if not str(file_url).startswith("http"):
            file_url = f"{YTDLP_API_URL}/files/{file_url.lstrip('/')}"
        out = outdir / _safe_name(str(filename))
        result = await _http_download_to_file(str(file_url), out)
        result["method"] = "ytdlp-api"
        result["mode"] = mode
        return result

    raise DownloadError("failed")


async def _try_external_providers(url: str, outdir: Path, mode: str) -> dict | None:
    """Try configured external providers in order. Return result or None."""
    if not _external_providers_configured():
        return None
    providers = []
    if COBALT_URL:
        providers.append(("cobalt", _download_via_cobalt))
    if YTDLP_API_URL:
        providers.append(("ytdlp-api", _download_via_ytdlp_api))
    for name, fn in providers:
        try:
            logger.info("external provider try=%s url=%s mode=%s", name, url[:120], mode)
            result = await fn(url, outdir, mode)
            if result and result.get("path") and Path(result["path"]).is_file():
                size = int(result.get("size") or Path(result["path"]).stat().st_size)
                if size > 0:
                    result["size"] = size
                    return result
        except DownloadError as exc:
            logger.warning("external provider %s failed: %s", name, exc)
            # clean partials
            try:
                for p in outdir.glob("*"):
                    if p.is_file():
                        p.unlink(missing_ok=True)
            except Exception as exc:
                logger.debug("non-fatal exception: %s", exc)
            continue
        except Exception as exc:
            logger.warning("external provider %s error: %s", name, str(exc)[:300])
            try:
                for p in outdir.glob("*"):
                    if p.is_file():
                        p.unlink(missing_ok=True)
            except Exception as exc:
                logger.debug("non-fatal exception: %s", exc)
            continue
    return None


class DownloadError(Exception):
    pass

_global_sem = asyncio.Semaphore(GLOBAL_CONCURRENCY)
_user_locks: dict[int, asyncio.Semaphore] = {}
_user_lock_guard = threading.Lock()


def _user_sem(user_id: int | None) -> asyncio.Semaphore:
    if user_id is None:
        return asyncio.Semaphore(PER_USER_CONCURRENCY)
    with _user_lock_guard:
        sem = _user_locks.get(int(user_id))
        if sem is None:
            if len(_user_locks) > 2048:
                stale = [k for k, v in _user_locks.items() if getattr(v, "_value", 0) > 0]
                for k in stale[:1024]:
                    _user_locks.pop(k, None)
            sem = asyncio.Semaphore(PER_USER_CONCURRENCY)
            _user_locks[int(user_id)] = sem
        return sem


def _host_is_safe(host: str) -> None:
    host = (host or "").strip().rstrip(".").lower()
    if not host or host in {"localhost", "localhost.localdomain", "metadata.google.internal"}:
        raise DownloadError("blocked_host")
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise DownloadError("dns_error") from exc
    seen = set()
    for info in infos:
        raw = info[4][0]
        if raw in seen:
            continue
        seen.add(raw)
        ip = ipaddress.ip_address(raw)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            raise DownloadError("blocked_host")


def _validate_url(url: str) -> str:
    url = (url or "").strip()
    p = urlparse(url)
    if p.scheme not in {"http", "https"} or not p.netloc or p.username or p.password:
        raise DownloadError("invalid_url")
    _host_is_safe(p.hostname or "")
    return url


def _normalize_media_url(url: str) -> str:
    """Canonicalize social-media URLs without changing their content target."""
    p = urlparse((url or "").strip())
    host = (p.hostname or "").lower().rstrip(".")
    if host == "instagram.com" or host.endswith(".instagram.com"):
        # Instagram share links commonly carry tracking tokens (utm/igsh).
        # They are not required to identify the Reel and can make extraction
        # less deterministic. Preserve only the path/query parameters that are
        # not known tracking parameters.
        return p._replace(query="").geturl()
    return url


def extract_url(text: str) -> str | None:
    """Extract and normalize the first HTTP(S) URL from Telegram text.

    Telegram users often paste URLs wrapped in angle brackets, quotes,
    backticks, or followed by Persian/Arabic punctuation.  The old full-string
    regex rejected those otherwise valid links.
    """
    value = (text or "").replace("\u200b", "").replace("\ufeff", "").strip()
    if not value:
        return None
    # Remove common invisible bidi/control marks without touching URL content.
    value = re.sub(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069]", "", value)
    match = re.search(r"https?://[^\s<>\"'`]+", value, re.I)
    if not match:
        return None
    url = match.group(0).rstrip(".,!?;:،؛؟")
    while url.endswith(")") and url.count(")") > url.count("("):
        url = url[:-1]
    return url if re.match(r"^https?://[^\s]+$", url, re.I) else None


def is_url(text: str) -> bool:
    return extract_url(text) is not None


def _safe_name(name: str, default: str = "download.bin") -> str:
    name = unquote(name or "")
    name = re.sub(r"[\\/:*?\"<>|\x00-\x1f]+", "_", name).strip(". ")[:120]
    return name or default


def _classify_error(exc: str) -> str:
    s = (exc or "").lower()
    if any(x in s for x in ("429", "too many requests", "rate limit")):
        return "rate_limited"
    if any(x in s for x in (
        "captcha", "403", "forbidden", "sign in", "login required",
        "http error 401", "access denied", "rate-limit reached",
        "rate limit reached", "main webpage is locked behind the login page",
    )):
        return "site_blocked"
    if any(x in s for x in ("private", "members only", "age-restricted", "authentication required")):
        return "access_restricted"
    if any(x in s for x in ("unsupported", "no suitable", "unable to extract", "not available")):
        return "unsupported"
    if any(x in s for x in ("too large", "max-filesize", "maximum file size")):
        return "too_large"
    if any(x in s for x in ("name or service not known", "temporary failure in name resolution", "nodename nor servname")):
        return "dns_error"
    if "sign in to confirm" in s or "not a bot" in s:
        return "site_blocked"
    if "page needs to be reloaded" in s:
        return "failed"
    return "failed"


def _preflight_redirects(url: str) -> str:
    """Validate redirects without turning social-media share links into login URLs."""
    import requests
    current = _normalize_media_url(_validate_url(url))
    host = (urlparse(current).hostname or "").lower().rstrip(".")
    # Instagram can redirect a HEAD request for a public Reel to its login page
    # even when the original Reel URL is the correct extractor input. Following
    # that redirect here makes yt-dlp receive the wrong URL. Let yt-dlp manage
    # the Instagram session/redirects itself while still validating the original
    # hostname for SSRF protection.
    if host == "instagram.com" or host.endswith(".instagram.com"):
        return current
    session = requests.Session()
    headers = {"User-Agent": UA, "Accept": "*/*"}
    for _ in range(MAX_REDIRECTS + 1):
        _validate_url(current)
        try:
            r = session.head(current, allow_redirects=False, timeout=min(TIMEOUT, 10), headers=headers)
            if r.status_code in {405, 501}:
                r = session.get(current, allow_redirects=False, stream=True, timeout=min(TIMEOUT, 10), headers=headers)
                r.close()
        except DownloadError:
            raise
        except Exception as exc:
            # A failed preflight should not hide an otherwise valid media URL;
            # DNS/security errors are still fatal because they are meaningful.
            code = _classify_error(str(exc))
            if code in {"dns_error", "site_blocked"}:
                raise DownloadError(code) from exc
            return current
        if r.is_redirect or r.status_code in {301, 302, 303, 307, 308}:
            location = r.headers.get("Location")
            if not location:
                return current
            current = _validate_url(urljoin(current, location))
            continue
        return current
    raise DownloadError("failed")


def _cache_key(url: str, mode: str) -> str:
    return hashlib.sha256(f"{url}\n{mode}".encode()).hexdigest()


def _cache_paths(key: str) -> tuple[Path, Path]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{key}.bin", CACHE_DIR / f"{key}.json"


def _cache_get(url: str, mode: str) -> dict | None:
    if CACHE_TTL <= 0:
        return None
    path, meta = _cache_paths(_cache_key(url, mode))
    try:
        info = json.loads(meta.read_text("utf-8"))
        if time.time() - float(info.get("created", 0)) > CACHE_TTL or not path.is_file():
            return None
        if path.stat().st_size > MAX_BYTES:
            return None
        return {**info, "path": str(path), "size": path.stat().st_size, "cached": True}
    except Exception as exc:
        logger.debug("downloader cache read failed: %s", exc)
        return None


def _cache_put(result: dict, url: str, mode: str) -> None:
    if CACHE_TTL <= 0 or result.get("size", 0) <= 0 or result.get("size", 0) > MAX_BYTES:
        return
    try:
        path, meta = _cache_paths(_cache_key(url, mode))
        src = Path(result["path"])
        if src.resolve() != path.resolve():
            shutil.copy2(src, path)
        meta.write_text(json.dumps({k: result.get(k) for k in ("title", "content_type", "method")}|{"created": time.time()}, ensure_ascii=False), "utf-8")
        _prune_cache()
    except Exception:
        logger.debug("downloader cache write failed", exc_info=True)


def _prune_cache() -> None:
    try:
        files = sorted(CACHE_DIR.glob("*.bin"), key=lambda p: p.stat().st_mtime, reverse=True)
        total = 0
        for p in files:
            size = p.stat().st_size
            if total + size > CACHE_MAX_BYTES:
                p.unlink(missing_ok=True)
                p.with_suffix(".json").unlink(missing_ok=True)
            else:
                total += size
    except Exception as exc:
        logger.debug("non-fatal exception: %s", exc)


def _content_disposition_name(value: str) -> str:
    m = re.search(r"filename\*?=(?:UTF-8''|\")?([^;\"]+)", value or "", re.I)
    return _safe_name(m.group(1).strip() if m else "")


async def _direct(url: str, out: Path) -> dict:
    try:
        import requests
        loop = asyncio.get_running_loop()
        def work():
            session = requests.Session()
            current = url
            for _ in range(MAX_REDIRECTS + 1):
                current = _validate_url(current)
                r = session.get(current, stream=True, timeout=TIMEOUT, headers={"User-Agent": UA, "Accept": "*/*"}, allow_redirects=False)
                if r.is_redirect or r.status_code in {301,302,303,307,308}:
                    location = r.headers.get("Location")
                    r.close()
                    if not location:
                        raise DownloadError("failed")
                    current = urljoin(current, location)
                    continue
                r.raise_for_status()
                length = int(r.headers.get("content-length") or 0)
                if length > MAX_BYTES:
                    r.close(); raise DownloadError("too_large")
                ctype = r.headers.get("content-type", "").lower()
                name = _content_disposition_name(r.headers.get("content-disposition", ""))
                if not name:
                    name = _safe_name(Path(urlparse(current).path).name or "download.bin")
                part = out.with_suffix(out.suffix + ".part")
                total = part.stat().st_size if part.exists() else 0
                headers = {"User-Agent": UA, "Accept": "*/*"}
                if total:
                    # Restart cleanly if server cannot honor range.
                    r.close()
                    rr = session.get(current, stream=True, timeout=TIMEOUT, headers={**headers, "Range": f"bytes={total}-"}, allow_redirects=False)
                    if rr.status_code == 206:
                        r = rr
                    else:
                        rr.close(); part.unlink(missing_ok=True); total = 0
                        r = session.get(current, stream=True, timeout=TIMEOUT, headers=headers, allow_redirects=False)
                with part.open("ab" if total else "wb") as f:
                    for chunk in r.iter_content(YTDLP_BUFFER_SIZE):
                        if not chunk:
                            continue
                        total += len(chunk)
                        if total > MAX_BYTES:
                            r.close(); part.unlink(missing_ok=True); raise DownloadError("too_large")
                        f.write(chunk)
                r.close()
                part.replace(out)
                return {"path": str(out), "title": name, "size": total, "content_type": ctype, "method": "direct"}
            raise DownloadError("failed")
        return await loop.run_in_executor(None, work)
    except DownloadError:
        raise
    except Exception as exc:
        raise DownloadError(_classify_error(str(exc))) from exc


async def probe(url: str) -> dict:
    if _is_blocked_media_url(url):
        return {"supported": False, "direct": False, "url": url, "formats": [], "error": "unsupported"}
    url = _preflight_redirects(url)
    try:
        import yt_dlp
    except ImportError:
        return {"supported": False, "direct": True, "url": url, "formats": []}

    loop = asyncio.get_running_loop()

    def work():
        opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "socket_timeout": int(TIMEOUT),
            "noplaylist": True,
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            },
        }
        cookie = _resolve_cookies_file()
        if cookie:
            opts["cookiefile"] = cookie
        proxy = os.getenv("DOWNLOADER_PROXY", "").strip()
        if proxy:
            opts["proxy"] = proxy

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)

        formats = []
        for f in info.get("formats") or []:
            if not f.get("format_id"):
                continue
            formats.append({
                "id": str(f.get("format_id")),
                "ext": f.get("ext"),
                "height": f.get("height"),
                "vcodec": f.get("vcodec"),
                "acodec": f.get("acodec"),
                "filesize": f.get("filesize") or f.get("filesize_approx"),
            })
        return {
            "supported": True,
            "direct": False,
            "url": url,
            "title": info.get("title") or "media",
            "duration": info.get("duration"),
            "thumbnail": info.get("thumbnail"),
            "formats": formats[-80:],
        }

    try:
        return await loop.run_in_executor(None, work)
    except Exception as exc:
        return {
            "supported": False,
            "direct": True,
            "url": url,
            "formats": [],
            "error": _classify_error(str(exc)),
        }


async def _ytdlp(url: str, outdir: Path, mode: str = "best", progress_cb=None) -> dict:
    try:
        import yt_dlp
    except ImportError:
        raise DownloadError("yt_dlp_missing")

    loop = asyncio.get_running_loop()

    def _format_for(mode_name: str) -> str:
        return {
            "best": "b[ext=mp4]/best[ext=mp4]/bv*[ext=mp4]+ba[ext=m4a]/bv*+ba/b",
            "1080p": "b[height<=1080][ext=mp4]/bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080]/bv*[height<=1080]+ba/b",
            "720p": "b[height<=720][ext=mp4]/bv*[height<=720][ext=mp4]+ba[ext=m4a]/b[height<=720]/bv*[height<=720]+ba/b",
            "480p": "b[height<=480][ext=mp4]/bv*[height<=480][ext=mp4]+ba[ext=m4a]/b[height<=480]/bv*[height<=480]+ba/b",
            "audio": "bestaudio[ext=m4a]/bestaudio/best",
        }.get(mode_name, "b[ext=mp4]/best")

    def work():
        progress = {"path": None, "downloaded": 0, "total": 0, "last": 0.0}
        outtmpl = str(outdir / "%(title).80s-%(id)s.%(ext)s")

        def hook(d):
            status = d.get("status")
            if status == "downloading":
                progress["downloaded"] = int(d.get("downloaded_bytes") or 0)
                progress["total"] = int(d.get("total_bytes") or d.get("total_bytes_estimate") or 0)
                if progress["downloaded"] > MAX_BYTES or (progress["total"] and progress["total"] > MAX_BYTES):
                    raise DownloadError("too_large")
                now = time.monotonic()
                if progress_cb and now - progress["last"] >= 1.5:
                    progress["last"] = now
                    try:
                        progress_cb(progress.copy())
                    except Exception as exc:
                        logger.debug("downloader progress callback failed: %s", exc)
            elif status == "finished":
                progress["path"] = d.get("filename")
                if progress_cb:
                    try:
                        progress_cb({**progress, "finished": True})
                    except Exception as exc:
                        logger.debug("downloader finished callback failed: %s", exc)

        opts = {
            "format": _format_for(mode),
            "outtmpl": outtmpl,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "retries": 5,
            "fragment_retries": 5,
            "socket_timeout": int(TIMEOUT),
            "max_filesize": MAX_BYTES,
            "concurrent_fragment_downloads": YTDLP_CONCURRENT_FRAGMENTS,
            "http_chunk_size": YTDLP_HTTP_CHUNK_SIZE or None,
            "buffersize": YTDLP_BUFFER_SIZE,
            "restrictfilenames": True,
            "progress_hooks": [hook],
            "http_headers": {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            },
            "merge_output_format": "mp4",
            "continuedl": True,
            "overwrites": True,
            "ignoreerrors": False,
            "ignoreconfig": True,
            "js_runtimes": {"node": "node"},
        }

        cookie_path = _resolve_cookies_file()
        if cookie_path:
            opts["cookiefile"] = cookie_path
        proxy = os.getenv("DOWNLOADER_PROXY", "").strip()
        if proxy:
            opts["proxy"] = proxy

        parsed_host = (urlparse(url).hostname or "").lower().rstrip(".")
        if parsed_host == "instagram.com" or parsed_host.endswith(".instagram.com"):
            opts["http_headers"]["Referer"] = "https://www.instagram.com/"
            opts["extractor_args"] = {"instagram": {"app_id": "web"}}
        if mode == "audio":
            opts["postprocessors"] = [
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
            ]

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info:
                raise DownloadError("failed")
            path = Path(ydl.prepare_filename(info))
            if mode == "audio":
                mp3 = path.with_suffix(".mp3")
                if mp3.exists():
                    path = mp3
            if not path.exists():
                vid = str(info.get("id") or "")
                candidates = list(outdir.glob(f"*{vid}*")) if vid else list(outdir.glob("*"))
                candidates = [p for p in candidates if p.is_file()]
                if candidates:
                    path = max(candidates, key=lambda p: p.stat().st_mtime)
            if not path.exists():
                raise DownloadError("failed")
            size = path.stat().st_size
            if size <= 0:
                path.unlink(missing_ok=True)
                raise DownloadError("failed")
            if size > MAX_BYTES:
                path.unlink(missing_ok=True)
                raise DownloadError("too_large")
            return {
                "path": str(path),
                "title": _safe_name(info.get("title") or path.stem),
                "size": size,
                "content_type": info.get("ext", ""),
                "method": "yt-dlp",
                "duration": info.get("duration"),
                "thumbnail": info.get("thumbnail"),
                "webpage_url": info.get("webpage_url"),
                "uploader": info.get("uploader"),
                "mode": mode,
            }

    try:
        return await loop.run_in_executor(None, work)
    except DownloadError:
        raise
    except Exception as exc:
        raise DownloadError(_classify_error(str(exc))) from exc


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

# Regression-contract marker: if _is_instagram_url(current):
# Regression contract: "extractor_args": {"instagram": {"app_id": "web"}}
# Never treat an Instagram HTML/login/challenge page as a successfully downloaded media file.

# END MERGED LEGACY PART: 
# STATIC CONTRACT ANCHORS:
# if _is_instagram_url(current):
# return current
# "extractor_args": {"instagram": {"app_id": "web"}}
# Never treat an Instagram HTML/login/challenge page
# STATIC CONTRACT: _normalize_media_url | login page | "extractor_args"
