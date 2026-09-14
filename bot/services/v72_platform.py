"""V72 production-quality extensions.

Scope: Downloader 3.0, AI routing 2.0, Web Intelligence, Document Intelligence,
Market Intelligence, QA automation, and UX helpers.  No conversation-summary
engine is implemented here.
"""
from __future__ import annotations
from bot.utils.modular_loader import load_modular_part

import asyncio
import csv
import hashlib
import io
import ipaddress
import json
import os
import re
import socket
import subprocess
import sys
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from bot.database_core import get_db_connection, _execute_write
from bot.logger import logger

MAX_DOCUMENT_BYTES = max(1, int(os.getenv("V72_MAX_DOCUMENT_BYTES", str(12 * 1024 * 1024))))
MAX_DOCUMENT_CHARS = max(1000, int(os.getenv("V72_MAX_DOCUMENT_CHARS", "120000")))
WEB_TIMEOUT = max(5, float(os.getenv("V72_WEB_TIMEOUT", "15")))


load_modular_part(__file__, 'v72_platform_parts/part_001_init_v72_tables.py')


# ---------------- Downloader 3.0 ----------------
QUALITY_MODES = ("best", "1080p", "720p", "480p", "audio")


load_modular_part(__file__, 'v72_platform_parts/part_002_normalize_download_mode.py')


load_modular_part(__file__, 'v72_platform_parts/part_003_ytdlp_format.py')


load_modular_part(__file__, 'v72_platform_parts/part_004_format_options.py')


load_modular_part(__file__, 'v72_platform_parts/part_005_record_download.py')


load_modular_part(__file__, 'v72_platform_parts/part_006_update_download.py')


load_modular_part(__file__, 'v72_platform_parts/part_007_progress_percent.py')


# ---------------- AI Router 2.0 ----------------
load_modular_part(__file__, 'v72_platform_parts/part_008_RouteCandidate.py')


load_modular_part(__file__, 'v72_platform_parts/part_009_classify_ai_complexity.py')


load_modular_part(__file__, 'v72_platform_parts/part_010_route_candidates.py')


# ---------------- Web Intelligence ----------------

load_modular_part(__file__, 'v72_platform_parts/part_011_safe_web_url.py')


load_modular_part(__file__, 'v72_platform_parts/part_012__assert_public_host.py')


load_modular_part(__file__, 'v72_platform_parts/part_013_dedupe_sources.py')


load_modular_part(__file__, 'v72_platform_parts/part_014_fetch_web_page.py')


load_modular_part(__file__, 'v72_platform_parts/part_015_verify_claims_against_sources.py')


load_modular_part(__file__, 'v72_platform_parts/part_016_web_intelligence_search.py')


# ---------------- Document Intelligence ----------------

load_modular_part(__file__, 'v72_platform_parts/part_017__safe_member.py')


load_modular_part(__file__, 'v72_platform_parts/part_018_extract_document.py')


load_modular_part(__file__, 'v72_platform_parts/part_019_store_document.py')


load_modular_part(__file__, 'v72_platform_parts/part_020_document_context.py')


# ---------------- Market Intelligence ----------------
load_modular_part(__file__, 'v72_platform_parts/part_021_market_intelligence.py')


load_modular_part(__file__, 'v72_platform_parts/part_022_market_summary.py')


# ---------------- QA / Ruff ----------------
load_modular_part(__file__, 'v72_platform_parts/part_023_run_ruff.py')


load_modular_part(__file__, 'v72_platform_parts/part_024_run_compile.py')


load_modular_part(__file__, 'v72_platform_parts/part_025_qa_snapshot.py')


# ---------------- UX ----------------
TEXTS = {
    "fa": {"download_title":"📥 دانلودر فایل حرفه‌ای","intro":"✨ لینک دانلودت رو همین‌جا بفرست!\n\n🎬 YouTube • 📸 Instagram • 🎵 TikTok • 📘 Facebook\n🌐 و کلی سایت دیگه + لینک مستقیم فایل\n\n🚀 سریع، ساده و حرفه‌ای","invalid":"❌ لینک معتبر http/https بفرستید.","checking":"🔎 در حال بررسی لینک و کیفیت‌های قابل دریافت…","downloading":"⏬ در حال دانلود…","ready":"✅ فایل آماده شد.","cancelled":"❌ دانلود لغو شد.","expired":"⚠️ این درخواست منقضی شده است. لینک را دوباره بفرستید.","prepared":"📥 لینک آماده است","choose":"فرمت/کیفیت را انتخاب کنید:","sending":"در حال ارسال…","probe_failed":"⚠️ بررسی لینک ناموفق بود. دوباره امتحان کنید."},
    "en": {"download_title":"📥 Professional File Downloader","intro":"✨ Send your download link here!\n\n🎬 YouTube • 📸 Instagram • 🎵 TikTok • 📘 Facebook\n🌐 And many more sites + direct file links\n\n🚀 Fast, simple and professional","invalid":"❌ Send a valid http/https URL.","checking":"🔎 Checking the link and available qualities…","downloading":"⏬ Downloading…","ready":"✅ File is ready.","cancelled":"❌ Download cancelled.","expired":"⚠️ This request has expired. Send the link again.","prepared":"📥 Link is ready","choose":"Choose format/quality:","sending":"Sending…","probe_failed":"⚠️ Link inspection failed. Please try again."},
    "ar": {"download_title":"📥 مُنزّل الملفات الاحترافي","intro":"✨ أرسل رابط التنزيل هنا!\n\n🎬 YouTube • 📸 Instagram • 🎵 TikTok • 📘 Facebook\n🌐 والعديد من المواقع الأخرى + روابط الملفات المباشرة\n\n🚀 سريع، بسيط واحترافي","invalid":"❌ أرسل رابط http/https صالحاً.","checking":"🔎 جارٍ فحص الرابط والجودات المتاحة…","downloading":"⏬ جارٍ التنزيل…","ready":"✅ الملف جاهز.","cancelled":"❌ تم إلغاء التنزيل.","expired":"⚠️ انتهت صلاحية هذا الطلب. أرسل الرابط مرة أخرى.","prepared":"📥 الرابط جاهز","choose":"اختر الصيغة/الجودة:","sending":"جارٍ الإرسال…","probe_failed":"⚠️ تعذر فحص الرابط. حاول مرة أخرى."},
}


load_modular_part(__file__, 'v72_platform_parts/part_026_ux_text.py')
