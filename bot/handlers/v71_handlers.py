from __future__ import annotations
from bot.utils.modular_loader import load_modular_part
import asyncio, re, secrets
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.logger import logger
from bot.services.downloader import is_url, extract_url, probe, download, cleanup, user_message
from bot.services.v71_platform import (
    SUPPORTED_LANGS, detect_language, personalize, self_test, set_workspace,
    get_workspace, save_branch, list_branches, schedule_ai,
)
from bot.services.v72_platform import format_options, record_download, update_download, normalize_download_mode, ux_text

load_modular_part(__file__, 'v71_handlers_parts/part_001__dl_lang.py')


load_modular_part(__file__, 'v71_handlers_parts/part_002_downloader_entry_v71.py')

load_modular_part(__file__, 'v71_handlers_parts/part_003__start_probe.py')

load_modular_part(__file__, 'v71_handlers_parts/part_004_handle_downloader_url_v71.py')


load_modular_part(__file__, 'v71_handlers_parts/part_005__download_social_direct.py')

load_modular_part(__file__, 'v71_handlers_parts/part_006_download_callback.py')

load_modular_part(__file__, 'v71_handlers_parts/part_007_v71_command.py')

load_modular_part(__file__, 'v71_handlers_parts/part_008_v71_selftest_command.py')

load_modular_part(__file__, 'v71_handlers_parts/part_009_workspace_command.py')

load_modular_part(__file__, 'v71_handlers_parts/part_010_branch_command.py')

load_modular_part(__file__, 'v71_handlers_parts/part_011_schedule_ai_command.py')

load_modular_part(__file__, 'v71_handlers_parts/part_012_personalize_command.py')
