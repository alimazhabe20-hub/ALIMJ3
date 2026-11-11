"""Downloader package.

Public API:
  from bot.services.downloader import download, DownloadError, cleanup, user_message

Legacy paths still work:
  from bot.services.downloader import download  (this package)
  from bot.services.insta_downloader import download  (shim)
"""
from bot.services.downloader.core import (  # noqa: F401
    download,
    cleanup,
    user_message,
    DownloadError,
)

__all__ = [
    "download",
    "cleanup",
    "user_message",
    "DownloadError",
]
