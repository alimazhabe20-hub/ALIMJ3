"""Shared safety, idempotency and Telegram-delivery helpers for group handlers."""
from __future__ import annotations

import asyncio
import time
from typing import Optional

from telegram import Update
from telegram.error import BadRequest, Forbidden, NetworkError, RetryAfter, TimedOut

from bot.logger import logger

_DEDUP_TTL = 180.0
_DEDUP_MAX = 4096


def claim_group_update(update: Update, context, *, namespace: str = "reply") -> bool:
    """Atomically claim an update once per bot process; safe in async handlers."""
    message = update.effective_message
    chat = update.effective_chat
    if not message or not chat:
        return False
    now = time.monotonic()
    cache = context.bot_data.setdefault("_group_update_dedup", {})
    # A single synchronous section is atomic relative to other asyncio tasks.
    for key, stamp in list(cache.items()):
        if now - stamp > _DEDUP_TTL:
            cache.pop(key, None)
    key = (namespace, chat.id, message.message_id)
    if key in cache:
        return False
    cache[key] = now
    if len(cache) > _DEDUP_MAX:
        for old_key, _ in sorted(cache.items(), key=lambda item: item[1])[: len(cache) - _DEDUP_MAX]:
            cache.pop(old_key, None)
    return True


async def group_ai_access_allowed(update: Update, context, *, notify: bool = False) -> bool:
    """Enforce persisted AI/admin policy on every group entry point."""
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    if not chat or not user:
        return False
    try:
        from bot.handlers.group_settings import is_group_ai_enabled, group_admin_only
        if not is_group_ai_enabled(chat.id):
            if notify and message:
                await safe_group_reply(message, "⏸ هوش مصنوعی این گروه خاموش است. ادمین: /groupsettings")
            return False
        if group_admin_only(chat.id):
            from bot.handlers.group_mode import user_is_group_admin
            if not await user_is_group_admin(update, context):
                if notify and message:
                    await safe_group_reply(message, "⛔ استفاده از هوش مصنوعی فقط برای ادمین‌های گروه فعال است.")
                return False
        return True
    except Exception as exc:
        # Fail closed when the access policy cannot be read or checked.
        logger.warning("group access policy check failed closed: %s", exc)
        if notify and message:
            await safe_group_reply(message, "⚠️ بررسی دسترسی گروه موقتاً ممکن نیست. کمی بعد تلاش کن.")
        return False


async def safe_group_reply(message, text: str, **kwargs):
    """Send a group reply with bounded FloodWait handling and safe fallbacks."""
    try:
        return await message.reply_text(text, **kwargs)
    except RetryAfter as exc:
        delay = getattr(exc, "retry_after", 1)
        try:
            delay = float(delay.total_seconds() if hasattr(delay, "total_seconds") else delay)
        except Exception:
            delay = 1.0
        if delay > 8:
            logger.warning("Telegram flood control: retry_after=%.1fs", delay)
            return None
        await asyncio.sleep(max(0.5, delay))
        try:
            return await message.reply_text(text, **kwargs)
        except Exception as retry_exc:
            logger.warning("group reply retry failed: %s", retry_exc)
            return None
    except (Forbidden, BadRequest) as exc:
        logger.info("group reply not permitted/invalid: %s", exc)
        return None
    except (TimedOut, NetworkError) as exc:
        logger.warning("group reply network error: %s", exc)
        return None
    except Exception as exc:
        logger.warning("group reply send failed: %s", exc)
        return None
