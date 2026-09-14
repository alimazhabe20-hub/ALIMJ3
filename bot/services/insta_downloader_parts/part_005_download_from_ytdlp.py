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
