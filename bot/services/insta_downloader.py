"""Instagram-oriented downloader cascade — ported from insta-downloader-bot.

Order (identical to the reference bot):
  1) gallery-dl
  2) yt-dlp

Returns a local file path. Caller is responsible for cleanup/send.
"""
from __future__ import annotations
from bot.utils.modular_loader import load_modular_part

import asyncio
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from bot.logger import logger

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".m4v"}


load_modular_part(__file__, 'insta_downloader_parts/part_001_is_instagram_url.py')


load_modular_part(__file__, 'insta_downloader_parts/part_002_is_social_url.py')


load_modular_part(__file__, 'insta_downloader_parts/part_003__normalize_instagram_url.py')


load_modular_part(__file__, 'insta_downloader_parts/part_004_download_from_gallery.py')


load_modular_part(__file__, 'insta_downloader_parts/part_005_download_from_ytdlp.py')


load_modular_part(__file__, 'insta_downloader_parts/part_006_download.py')


load_modular_part(__file__, 'insta_downloader_parts/part_007_is_video_path.py')


load_modular_part(__file__, 'insta_downloader_parts/part_008_cleanup_path.py')
