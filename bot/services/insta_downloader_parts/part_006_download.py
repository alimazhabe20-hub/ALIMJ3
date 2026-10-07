# Auto-split part 6: download
async def download(url: str) -> str:
    """Download Instagram/social media with an Instagram web-API fallback.

    Instagram public Reel pages can redirect logged-out requests to the login
    page. For Instagram, try the web GraphQL media endpoint first, then keep
    the normal gallery-dl/yt-dlp fallbacks for environments where cookies or a
    different extractor path is available.
    """
    url = _normalize_instagram_url(url)
    errors: list[str] = []

    # Instagram's public web GraphQL endpoint can expose the media URL even
    # when the Reel HTML page redirects to /accounts/login/.
    if is_instagram_url(url):
        try:
            path = await _download_instagram_graphql(url)
            logger.info("insta_downloader: Instagram GraphQL ok -> %s", path)
            return path
        except Exception as e:
            errors.append(f"instagram-api: {e}")
            logger.warning("insta_downloader Instagram GraphQL failed: %s", e)

    # Keep the reference project's proven fallback order.
    try:
        path = await download_from_gallery(url)
        logger.info("insta_downloader: gallery-dl ok -> %s", path)
        return path
    except Exception as e:
        errors.append(f"Gallery: {e}")
        logger.warning("insta_downloader gallery-dl failed, falling back to yt-dlp: %s", e)

    try:
        path = await download_from_ytdlp(url)
        logger.info("insta_downloader: yt-dlp ok -> %s", path)
        return path
    except Exception as e:
        errors.append(f"yt-dlp: {e}")
        logger.warning("insta_downloader yt-dlp failed: %s", e)

    raise RuntimeError("\n".join(errors) if errors else "download failed")


async def _download_instagram_graphql(url: str) -> str:
    """Resolve a public Instagram Reel through the web GraphQL endpoint."""
    import asyncio as _asyncio
    import json as _json
    import os as _os
    import re as _re
    import tempfile as _tempfile
    from pathlib import Path as _Path
    from urllib.parse import urlparse as _urlparse

    shortcode_match = _re.search(r"/(?:reel|reels|p)/([A-Za-z0-9_-]+)", url)
    if not shortcode_match:
        raise RuntimeError("Instagram post/reel shortcode not found")
    shortcode = shortcode_match.group(1)

    def work() -> str:
        try:
            import requests
        except ImportError as exc:
            raise RuntimeError("requests is not installed") from exc

        session = requests.Session()
        session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/128.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })

        home = session.get("https://www.instagram.com/", timeout=20, allow_redirects=True)
        home.raise_for_status()
        csrf = session.cookies.get("csrftoken")
        if not csrf:
            raise RuntimeError("Instagram did not provide csrftoken")

        doc_id = _os.getenv("INSTAGRAM_GRAPHQL_DOC_ID", "27128499623469141").strip()
        variables = {
            "shortcode": shortcode,
            "__relay_internal__pv__PolarisAIGMMediaWebLabelEnabledrelayprovider": False,
        }
        response = session.post(
            "https://www.instagram.com/graphql/query",
            params={"doc_id": doc_id},
            data={"variables": _json.dumps(variables, separators=(",", ":"))},
            headers={
                "Accept": "*/*",
                "Content-Type": "application/x-www-form-urlencoded",
                "X-CSRFToken": csrf,
                "X-IG-App-ID": "936619743392459",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "https://www.instagram.com/",
            },
            timeout=25,
        )
        response.raise_for_status()
        payload = response.json()
        items = (((payload.get("data") or {}).get("xdt_api__v1__media__shortcode__web_info") or {}).get("items") or [])
        if not items:
            raise RuntimeError("Instagram GraphQL returned no media")

        media = items[0]
        candidates: list[str] = []
        for version in media.get("video_versions") or []:
            candidate = version.get("url")
            if candidate:
                candidates.append(candidate)
        if not candidates:
            # Some public posts expose the video URL in a nested image/media
            # structure. Keep this small fallback for API shape changes.
            for item in media.get("carousel_media") or []:
                for version in item.get("video_versions") or []:
                    candidate = version.get("url")
                    if candidate:
                        candidates.append(candidate)

        if not candidates:
            raise RuntimeError("Instagram response contained no video URL")

        media_url = candidates[0]
        out_dir = _Path(_tempfile.mkdtemp(prefix="alimj3_ig_"))
        out_path = out_dir / f"instagram_{shortcode}.mp4"
        with session.get(
            media_url,
            headers={"Referer": "https://www.instagram.com/", "Accept": "*/*"},
            stream=True,
            timeout=(20, 120),
        ) as download_response:
            download_response.raise_for_status()
            with out_path.open("wb") as fh:
                for chunk in download_response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        fh.write(chunk)

        if not out_path.is_file() or out_path.stat().st_size < 1024:
            raise RuntimeError("Instagram media download produced an empty file")
        return str(out_path)

    loop = _asyncio.get_running_loop()
    return await loop.run_in_executor(None, work)
