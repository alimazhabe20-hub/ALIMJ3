"""downloader: validation responsibilities."""
from .downloader_common import *  # noqa: F401,F403
from . import downloader_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


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
