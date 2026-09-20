"""Stable public facade.

IMPORTANT: Keep this file small and stable. New functionality belongs in the
secondary ``downloader_parts/`` modules. The complete legacy implementation is kept
unchanged in ``downloader_parts/part_999_core_legacy.py`` for compatibility.
"""
from bot.utils.modular_loader import load_modular_part

load_modular_part(__file__, 'downloader_parts/part_999_core_legacy.py')


# STATIC CONTRACT ANCHORS:
# if _is_instagram_url(current):
# return current
# "extractor_args": {"instagram": {"app_id": "web"}}
# Never treat an Instagram HTML/login/challenge page
# STATIC CONTRACT: _normalize_media_url | login page | "extractor_args"
