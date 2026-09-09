from collections import defaultdict
import time
from telegram import Update
from telegram.ext import ContextTypes
from bot.config import config
from bot.logger import logger
from bot.database import get_user, save_user, get_user_language
from bot.utils.texts import TEXTS

# تاریخچه زمان پیام‌ها برای هر کاربر
_user_hits = defaultdict(list)
# تا این زمان کاربر موقتاً بلاک است (ضد اسپم)
_user_block_until = defaultdict(float)
# آخرین باری که به کاربر پیام هشدار دادیم (جلوگیری از اسپم هشدار)
_last_warn = defaultdict(float)


def _is_admin(user_id: int) -> bool:
    return user_id in getattr(config, "ADMIN_IDS", [])


def _smart_antispam(user_id: int) -> tuple[bool, str | None]:
    """
    ضد اسپم هوشمند — بدون سقف ثابت پیام برای کاربر عادی.

    قوانین:
    - استفاده عادی: آزاد
    - انفجار پیام (مثلاً ۸ تا در ۲ ثانیه): بلاک کوتاه ۵–۱۰ ثانیه
    - اسپم شدید (۱۵ تا در ۵ ثانیه): بلاک ۳۰ ثانیه
    - اسپم خیلی شدید (۳۰ تا در ۱۰ ثانیه): بلاک ۶۰ ثانیه
    """
    now = time.time()

    # اگر هنوز در دوره بلاک است
    until = _user_block_until.get(user_id, 0)
    if now < until:
        remain = int(until - now) + 1
        return False, f"⏳ کمی سریع بودی. {remain} ثانیه صبر کن."

    # پاک کردن تاریخچه قدیمی‌تر از ۳۰ ثانیه
    hits = [t for t in _user_hits[user_id] if now - t < 30]
    hits.append(now)
    _user_hits[user_id] = hits

    in_2s = sum(1 for t in hits if now - t <= 2)
    in_5s = sum(1 for t in hits if now - t <= 5)
    in_10s = sum(1 for t in hits if now - t <= 10)

    block_sec = 0
    if in_10s >= 30:
        block_sec = 60
    elif in_5s >= 15:
        block_sec = 30
    elif in_2s >= 8:
        block_sec = 8

    if block_sec:
        _user_block_until[user_id] = now + block_sec
        logger.warning(
            f"Antispam: user {user_id} blocked {block_sec}s "
            f"(2s={in_2s}, 5s={in_5s}, 10s={in_10s})"
        )
        return False, f"⏳ ارسال خیلی سریع بود. {block_sec} ثانیه صبر کن."

    return True, None


async def _maybe_warn(update: Update, text: str):
    """هشدار را حداکثر هر ۴ ثانیه یک‌بار نشان بده"""
    if not update.effective_user:
        return
    uid = update.effective_user.id
    now = time.time()
    if now - _last_warn[uid] < 4:
        # برای callback فقط answer خالی
        if update.callback_query:
            try:
                await update.callback_query.answer()
            except Exception as _exc:
                logger.debug("%s: %s", __name__, _exc)
        return
    _last_warn[uid] = now
    try:
        if update.message:
            await update.message.reply_text(text)
        elif update.callback_query:
            await update.callback_query.answer(text, show_alert=True)
    except Exception as _exc:
        logger.debug("%s: %s", __name__, _exc)


async def rate_limit_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """ضد اسپم هوشمند — بدون سقف ثابت پیام"""
    if not update.effective_user:
        return True
    user_id = update.effective_user.id
    if _is_admin(user_id):
        return True

    ok, msg = _smart_antispam(user_id)
    if not ok:
        await _maybe_warn(update, msg or "⏳ کمی صبر کن.")
        return False
    return True


async def start_rate_limit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """ضد اسپم برای /start — فقط جلوی اسپم پشت‌سرهم را می‌گیرد"""
    if not update.effective_user:
        return True
    user_id = update.effective_user.id
    if _is_admin(user_id):
        return True

    ok, msg = _smart_antispam(user_id)
    if not ok:
        await _maybe_warn(update, msg or "⏳ کمی صبر کن.")
        return False
    return True


async def check_membership(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Return True when no channel lock is configured or the user is a member/admin."""
    if not update.effective_user:
        return False
    user_id = update.effective_user.id
    if _is_admin(user_id):
        return True
    if not getattr(config, "FORCE_JOIN_ENABLED", True):
        return True  # force-join explicitly disabled
    channel_id = int(getattr(config, "REQUIRED_CHANNEL_ID", 0) or 0)
    channel_link = str(getattr(config, "REQUIRED_CHANNEL_LINK", "") or "").strip()
    if not channel_id or not channel_link:
        logger.error("Force-join is enabled but CHANNEL_ID or CHANNEL_LINK is not configured")
        return False
    try:
        member = await context.bot.get_chat_member(channel_id, user_id)
        if member.status in ["member", "administrator", "creator"]:
            return True
        # Telegram may report users with limited posting rights as RESTRICTED
        # while they are still members of the channel.
        if member.status == "restricted" and bool(getattr(member, "is_member", False)):
            return True
    except Exception as e:
        logger.error(f"Membership check failed for {user_id}: {e}")
        # Fail closed: force-join must remain enforced when enabled.
        return False
    return False


async def ensure_user_registered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user:
        return
    user = update.effective_user
    if not get_user(user.id):
        save_user(user.id, user.first_name or "کاربر")
        logger.info(f"New user registered: {user.id}")


async def check_and_rate_limit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """عضویت + ضد اسپم هوشمند (بدون سقف ثابت پیام)"""
    if not update.effective_user:
        return False

    await ensure_user_registered(update, context)

    # Force-join is enforced for every user-facing update, including /start.
    # This prevents the entry-point from becoming a bypass around the channel lock.
    if not await check_membership(update, context):
        lang = get_user_language(update.effective_user.id)
        text = TEXTS.get(lang, TEXTS["fa"])["not_member"].format(
            channel_link=config.REQUIRED_CHANNEL_LINK
        )
        if update.message:
            await update.message.reply_text(text)
        elif update.callback_query:
            await update.callback_query.answer("لطفاً ابتدا در کانال عضو شوید", show_alert=True)
            try:
                if update.callback_query.message:
                    await update.callback_query.message.reply_text(text)
            except Exception as _exc:
                logger.debug("%s: %s", __name__, _exc)
        return False

    return await rate_limit_middleware(update, context)
