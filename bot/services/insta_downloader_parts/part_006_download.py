# Auto-split part 6: download
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
