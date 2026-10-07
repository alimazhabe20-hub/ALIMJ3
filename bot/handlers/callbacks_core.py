"""Stable public facade.

IMPORTANT: Keep this file small and stable. New functionality belongs in the
Shared callback helpers used by the action handlers.
"""

"""Ordered compatibility loader for cleaned source chunks."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import ContextTypes
from bot.database import get_user, get_user_city, set_last_main_msg_id
from bot.services.ai_service import (
    available_providers,
    set_selected_provider,
    get_selected_model,
)

# Compatibility guard: some older Render deployments may contain an ai_service.py
# that predates clear_history(). Do not let that stale module crash the whole bot
# during startup; preserve the same database cleanup behavior as the canonical
# implementation when the export is missing.
try:
    from bot.services.ai_service import clear_history
except ImportError:
    def clear_history(user_id: int, *, clear_long_term: bool = False) -> None:
        try:
            from bot.database import clear_ai_history_summary, delete_ai_memory
            clear_ai_history_summary(user_id)
            if clear_long_term:
                delete_ai_memory(user_id)
        except Exception:
            pass
from bot.utils.helpers import (
    build_message,
    get_refresh_button,
    get_main_keyboard, get_more_keyboard, get_ai_keyboard, get_ai_model_keyboard,
    get_calendar_buttons,
    get_calendar_text,
)
from bot.api.calendar import get_today_tehran
from bot.handlers.middleware import check_and_rate_limit
from bot.config import config
from bot.logger import logger
import jdatetime
import asyncio
import html
import re
from datetime import datetime, timedelta


def datetime_now_date(tz_name: str, add_days: int = 0) -> str:
    """Return the user's calendar date in the selected timezone."""
    try:
        from bot.features.market.economic_calendar import _tz
        return (datetime.now(_tz(tz_name)) + timedelta(days=add_days)).strftime("%Y-%m-%d")
    except Exception:
        return (datetime.now() + timedelta(days=add_days)).strftime("%Y-%m-%d")


# جلوگیری از اجرای همزمان چند بروزرسانی برای یک کاربر
_refresh_locks = {}


def _get_refresh_lock(user_id: int):
    lock = _refresh_locks.get(user_id)
    if lock is None:
        # Keep the per-user lock map bounded during long-running bot sessions.
        # Stale unlocked entries are safe to discard; active locks are preserved.
        if len(_refresh_locks) > 2048:
            stale = [uid for uid, item in _refresh_locks.items() if not item.locked()]
            for uid in stale[:1024]:
                _refresh_locks.pop(uid, None)
        lock = asyncio.Lock()
        _refresh_locks[user_id] = lock
    return lock


async def _safe_answer(query, text: str = None, show_alert: bool = False):
    """پاسخ به callback فقط یک‌بار؛ اگر قبلاً جواب داده شده باشد بی‌صدا رد می‌شود."""
    try:
        if text is None:
            await query.answer()
        else:
            await query.answer(text, show_alert=show_alert)
    except Exception as _exc:
        logger.debug("%s: %s", __name__, _exc)


def _set_ec_view(context, *, mode="today", impact="all", currency="", date_str=""):
    context.user_data["ec_view"] = {
        "mode": mode, "impact": impact, "currency": currency, "date_str": date_str,
    }


def _ec_view(context):
    view = context.user_data.get("ec_view") or {}
    return {
        "mode": view.get("mode", "today"),
        "impact": view.get("impact", "all"),
        "currency": view.get("currency", ""),
        "date_str": view.get("date_str", ""),
    }

# ===== end merged part =====


