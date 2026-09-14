from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import ContextTypes
from bot.database import get_user, get_user_city, set_last_main_msg_id
from bot.services.ai_service import (
    clear_history,
    available_providers,
    set_selected_provider,
    get_selected_model,
)
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

from bot.utils.modular_loader import load_modular_part

load_modular_part(__file__, 'callbacks_parts/01_economic_calendar.py')
load_modular_part(__file__, 'callbacks_parts/02_ai_models.py')
load_modular_part(__file__, 'callbacks_parts/03_ai_models_back.py')
load_modular_part(__file__, 'callbacks_parts/04_ai_noop.py')
load_modular_part(__file__, 'callbacks_parts/05_ai_provider_model.py')
load_modular_part(__file__, 'callbacks_parts/06_ai_clear_memory.py')
load_modular_part(__file__, 'callbacks_parts/07_ai_continue.py')
load_modular_part(__file__, 'callbacks_parts/08_ai_exit.py')
load_modular_part(__file__, 'callbacks_parts/09_ai_tts.py')
load_modular_part(__file__, 'callbacks_parts/10_ai_quick.py')
load_modular_part(__file__, 'callbacks_parts/11_refresh_main.py')
load_modular_part(__file__, 'callbacks_parts/12_back_to_main.py')
load_modular_part(__file__, 'callbacks_parts/13_calendar_today.py')
load_modular_part(__file__, 'callbacks_parts/14_calendar_day.py')
load_modular_part(__file__, 'callbacks_parts/15_calendar_nav.py')
load_modular_part(__file__, 'callbacks_parts/16_cx.py')


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not await check_and_rate_limit(update, context):
        await _safe_answer(query)
        return
    data = query.data
    user_id = update.effective_user.id

    if data and data.startswith('ec:'):
        await _handle_economic_calendar(query, update, context, data, user_id)
        return
    if data == 'ai_models':
        await _handle_ai_models(query, update, context, data, user_id)
        return
    if data == 'ai_models_back':
        await _handle_ai_models_back(query, update, context, data, user_id)
        return
    if data == 'ai_noop':
        await _handle_ai_noop(query, update, context, data, user_id)
        return
    if data.startswith('ai_provider:') or data.startswith('ai_model:'):
        await _handle_ai_provider_model(query, update, context, data, user_id)
        return
    if data == 'ai_clear_memory':
        await _handle_ai_clear_memory(query, update, context, data, user_id)
        return
    if data.startswith('ai_continue:'):
        await _handle_ai_continue(query, update, context, data, user_id)
        return
    if data == 'ai_exit':
        await _handle_ai_exit(query, update, context, data, user_id)
        return
    if data.startswith('ai_tts:'):
        await _handle_ai_tts(query, update, context, data, user_id)
        return
    if data.startswith('ai_quick:'):
        await _handle_ai_quick(query, update, context, data, user_id)
        return
    if data == 'refresh_main':
        await _handle_refresh_main(query, update, context, data, user_id)
        return
    if data == 'back_to_main':
        await _handle_back_to_main(query, update, context, data, user_id)
        return
    if data == 'calendar_today':
        await _handle_calendar_today(query, update, context, data, user_id)
        return
    if data.startswith('day_'):
        await _handle_calendar_day(query, update, context, data, user_id)
        return
    if data.startswith('cal_'):
        await _handle_calendar_nav(query, update, context, data, user_id)
        return
    if data.startswith('cx:'):
        await _handle_cx(query, update, context, data, user_id)
        return
    await _safe_answer(query)
