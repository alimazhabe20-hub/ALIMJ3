"""Shared imports and module state for the refactored downloader."""

from __future__ import annotations

"""Ordered compatibility loader for cleaned source chunks."""

"""Production downloader for public URLs.

Design goals: safe URL validation (including redirects), bounded concurrency,
per-user throttling, persistent small cache, resumable direct HTTP downloads,
metadata/format probing, and clear handling of site blocks.  It never bypasses
CAPTCHA, authentication, DRM, geo/access controls, or site bans.
"""

import asyncio

import hashlib

import ipaddress

import json

import os

import re

import shutil

import socket

import tempfile

import threading

import time

from pathlib import Path

from urllib.parse import unquote, urljoin, urlparse

from bot.logger import logger

MAX_BYTES = max(1, int(os.getenv("DOWNLOADER_MAX_BYTES", str(1024 * 1024 * 1024))))

TIMEOUT = max(5.0, float(os.getenv("DOWNLOADER_TIMEOUT", "60")))

MAX_REDIRECTS = max(1, int(os.getenv("DOWNLOADER_MAX_REDIRECTS", "5")))

GLOBAL_CONCURRENCY = max(1, int(os.getenv("DOWNLOADER_CONCURRENCY", "2")))

PER_USER_CONCURRENCY = max(1, int(os.getenv("DOWNLOADER_PER_USER_CONCURRENCY", "1")))

CACHE_TTL = max(0, int(os.getenv("DOWNLOADER_CACHE_TTL", "3600")))

CACHE_MAX_BYTES = max(MAX_BYTES, int(os.getenv("DOWNLOADER_CACHE_MAX_BYTES", str(1024 * 1024 * 1024))))

CACHE_DIR = Path(os.getenv("DOWNLOADER_CACHE_DIR", str(Path(tempfile.gettempdir()) / "alimj3_downloader_cache")))

UA = "Mozilla/5.0 (compatible; ALIMJ3-Downloader/2.0)"

_COOKIES_PATH_CACHE: str | None = None
