# Auto-split part 6: download
async def download(url: str) -> str:
    """Download a social-media URL using the reference cascade."""
    url = _normalize_instagram_url(url)
    errors: list[str] = []

    # Match the working reference bot: gallery-dl first, yt-dlp fallback.
    try:
        path = await download_from_gallery(url)
        logger.info("insta_downloader: gallery-dl ok → %s", path)
        return path
    except Exception as e:
        errors.append(f"Gallery: {e}")
        logger.warning("insta_downloader gallery-dl failed, falling back to yt-dlp: %s", e)

    try:
        path = await download_from_ytdlp(url)
        logger.info("insta_downloader: yt-dlp fallback ok → %s", path)
        return path
    except Exception as e:
        errors.append(f"yt-dlp: {e}")
        logger.warning("insta_downloader yt-dlp fallback failed: %s", e)

    raise RuntimeError("\n".join(errors) if errors else "download failed")
