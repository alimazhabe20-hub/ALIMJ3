"""downloader: providers responsibilities."""
from .downloader_common import *  # noqa: F401,F403
from . import downloader_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


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
