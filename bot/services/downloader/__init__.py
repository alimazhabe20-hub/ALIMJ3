"""Stable public API for the downloader package.

Keep this module as the single compatibility surface for handlers and services.
New downloader internals should remain in core.py / the specialized modules.
"""

from bot.services.downloader.core import (  # noqa: F401
    MAX_BYTES,
    DownloadError,
    is_url,
    extract_url,
    probe,
    download,
    cleanup,
    user_message,
)

__all__ = [
    "MAX_BYTES",
    "DownloadError",
    "is_url",
    "extract_url",
    "probe",
    "download",
    "cleanup",
    "user_message",
]
