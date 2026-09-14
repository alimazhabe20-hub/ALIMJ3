# Auto-split part 6: download
async def download(url: str) -> str:
    """Fast Instagram/social download cascade: yt-dlp first, gallery-dl fallback."""
    url = _normalize_instagram_url(url)
    errors: list[str] = []

    # yt-dlp is the fast path. Avoid starting gallery-dl first because a
    # slow/failing gallery-dl probe can add substantial latency to every job.
    try:
        path = await download_from_ytdlp(url)
        logger.info("insta_downloader: yt-dlp ok → %s", path)
        return path
    except Exception as e:
        errors.append(f"yt-dlp: {e}")
        logger.warning("insta_downloader yt-dlp failed, falling back to gallery-dl: %s", e)

    try:
        path = await download_from_gallery(url)
        logger.info("insta_downloader: gallery-dl fallback ok → %s", path)
        return path
    except Exception as e:
        errors.append(f"Gallery: {e}")
        logger.warning("insta_downloader gallery-dl fallback failed: %s", e)

    raise RuntimeError("\n".join(errors) if errors else "download failed")
