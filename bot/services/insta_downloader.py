"""Legacy flat module — Instagram/social cascade lives in downloader.instagram."""
from bot.services.downloader.instagram import *  # noqa: F401,F403
from bot.services.downloader.instagram import (  # noqa: F401
    download,
    download_from_gallery,
    download_from_ytdlp,
    is_social_url,
    is_instagram_url,
    is_video_path,
    cleanup_path,
)
