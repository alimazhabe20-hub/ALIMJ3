"""Downloader package.

Public API:
  from bot.services.downloader import (
      is_url, extract_url, download, DownloadError, cleanup, user_message
  )

Legacy paths still work:
  from bot.services.downloader import download
  from bot.services.insta_downloader import download
"""

from bot.services.downloader.core import (  # noqa: F401
    is_url,
    extract_url,
    download,
    cleanup,
    user_message,
    DownloadError,
)

__all__ = [
    "is_url",
    "extract_url",
    "download",
    "cleanup",
    "user_message",
    "DownloadError",
]
