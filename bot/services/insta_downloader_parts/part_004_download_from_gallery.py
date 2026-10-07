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
