"""Telegram callback router.

Business logic is split into focused action modules.
"""
from telegram import Update
from telegram.ext import ContextTypes
from bot.handlers.middleware import check_and_rate_limit
from bot.logger import logger
from bot.handlers.callbacks_core import _safe_answer

# ===== merged from bot/handlers/callbacks_parts/handlers_callbacks_parts_handlers_callbacks_parts_part_999_core_legacy_chunk_02.py =====

from bot.handlers.callbacks_actions.handle_economic_calendar import handle as _handle_economic_calendar
from bot.handlers.callbacks_actions.handle_ai_models import handle as _handle_ai_models
from bot.handlers.callbacks_actions.handle_ai_models_2 import handle as _handle_ai_models_2
from bot.handlers.callbacks_actions.handle_action_4 import handle as _handle_action_4
from bot.handlers.callbacks_actions.handle_ai_model import handle as _handle_ai_model
from bot.handlers.callbacks_actions.handle_ai_memory import handle as _handle_ai_memory
from bot.handlers.callbacks_actions.handle_ai_continue import handle as _handle_ai_continue
from bot.handlers.callbacks_actions.handle_ai_exit import handle as _handle_ai_exit
from bot.handlers.callbacks_actions.handle_ai_tts import handle as _handle_ai_tts
from bot.handlers.callbacks_actions.handle_ai_quick import handle as _handle_ai_quick
from bot.handlers.callbacks_actions.handle_refresh_main import handle as _handle_refresh_main
from bot.handlers.callbacks_actions.handle_back_to_main import handle as _handle_back_to_main
from bot.handlers.callbacks_actions.handle_calendar_today import handle as _handle_calendar_today
from bot.handlers.callbacks_actions.handle_calendar_day import handle as _handle_calendar_day
from bot.handlers.callbacks_actions.handle_calendar_navigation import handle as _handle_calendar_navigation
from bot.handlers.callbacks_actions.handle_crypto_analysis import handle as _handle_crypto_analysis
from bot.handlers.reminder_handlers import (
    _find as _find_reminder,
    detail_text as _reminder_detail_text,
    detail_keyboard as _reminder_detail_keyboard,
    reminder_manager_text as _reminder_manager_text,
    reminder_manager_keyboard as _reminder_manager_keyboard,
)
from bot.database import set_reminder_active, delete_reminder
from bot.utils.helpers import get_profile_keyboard

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Thin callback router; business actions live in callbacks_actions/."""
    query = update.callback_query
    if not await check_and_rate_limit(update, context):
        await _safe_answer(query)
        return
    data = query.data
    if data and data.startswith('ec:'):
        await _handle_economic_calendar(update, context)
        return
    if data == 'ai_models':
        await _handle_ai_models(update, context)
        return
    if data == 'ai_models_back':
        await _handle_ai_models_2(update, context)
        return
    if data == 'ai_noop':
        await _handle_action_4(update, context)
        return
    if data.startswith('ai_provider:') or data.startswith('ai_model:'):
        await _handle_ai_model(update, context)
        return
    if data == 'ai_clear_memory':
        await _handle_ai_memory(update, context)
        return
    if data.startswith('ai_continue:'):
        await _handle_ai_continue(update, context)
        return
    if data == 'ai_exit':
        await _handle_ai_exit(update, context)
        return
    if data.startswith('ai_tts:'):
        await _handle_ai_tts(update, context)
        return
    if data.startswith('ai_quick:'):
        await _handle_ai_quick(update, context)
        return
    if data == 'refresh_main':
        await _handle_refresh_main(update, context)
        return
    if data == 'back_to_main':
        await _handle_back_to_main(update, context)
        return
    if data == 'calendar_today':
        await _handle_calendar_today(update, context)
        return
    if data.startswith('day_'):
        await _handle_calendar_day(update, context)
        return
    if data.startswith('cal_'):
        await _handle_calendar_navigation(update, context)
        return
    if data.startswith('cx:'):
        await _handle_crypto_analysis(update, context)
        return
    if data and data.startswith("rem:"):
        query = update.callback_query
        uid = update.effective_user.id
        action = data.split(":", 2)
        try:
            kind = action[1] if len(action) > 1 else ""
            rid = int(action[2]) if len(action) > 2 and action[2].isdigit() else None
            if kind == "list":
                text, rows = _reminder_manager_text(uid)
                await query.edit_message_text(text, reply_markup=_reminder_manager_keyboard(rows))
            elif kind == "profile":
                # ReplyKeyboardMarkup cannot be used with edit_message_text.
                await query.answer()
                await query.message.reply_text("👤 پروفایل:", reply_markup=get_profile_keyboard())
            elif kind == "add":
                context.user_data["waiting_for"] = "reminder_new"
                await query.edit_message_text("⏰ متن یادآوری را بفرست؛ مثلاً: «فردا ساعت ۹ جلسه دارم»\n\nبرای لغو: «لغو»")
            elif rid is None:
                await _safe_answer(query, "⚠️ درخواست نامعتبر است.", show_alert=True)
            else:
                row = _find_reminder(uid, rid)
                if not row:
                    await _safe_answer(query, "⚠️ این یادآوری پیدا نشد.", show_alert=True)
                elif kind == "view":
                    await query.edit_message_text(_reminder_detail_text(row), reply_markup=_reminder_detail_keyboard(row))
                elif kind == "toggle":
                    ok = set_reminder_active(uid, rid, not bool(int(row[6] or 0)))
                    if ok:
                        row = _find_reminder(uid, rid)
                        await query.edit_message_text(_reminder_detail_text(row), reply_markup=_reminder_detail_keyboard(row))
                    else:
                        await _safe_answer(query, "⚠️ تغییر وضعیت انجام نشد.", show_alert=True)
                elif kind == "delete":
                    ok = delete_reminder(uid, rid)
                    if ok:
                        text, rows = _reminder_manager_text(uid)
                        await query.edit_message_text(text, reply_markup=_reminder_manager_keyboard(rows))
                    else:
                        await _safe_answer(query, "⚠️ حذف انجام نشد.", show_alert=True)
                elif kind in {"text", "time"}:
                    context.user_data["reminder_edit"] = {"rid": rid, "mode": kind}
                    prompt = "📝 متن جدید را بفرست:" if kind == "text" else "🕐 زمان جدید را بفرست؛ مثلاً «فردا ساعت ۹»:"
                    await query.edit_message_text(prompt + "\n\nبرای لغو: «لغو»")
                else:
                    await _safe_answer(query)
            if kind != "profile":
                await _safe_answer(query)
        except Exception as exc:
            logger.exception("reminder callback failed: %s", exc)
            await _safe_answer(query, "⚠️ انجام این عملیات ممکن نشد.", show_alert=True)
        return
    await _safe_answer(query)



