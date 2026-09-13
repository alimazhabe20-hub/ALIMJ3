"""Advanced automatic Telegram message reactions.

The feature reacts only to high-confidence user text and never attempts to
bypass Telegram permissions, chat reaction restrictions, CAPTCHA, privacy, or
other access controls. It uses the official Bot API method setMessageReaction
through the existing httpx dependency so the project can keep its current
python-telegram-bot version.
"""
from __future__ import annotations

import re
import time
from collections import deque
from typing import Optional

import httpx

from bot.config import config
from bot.logger import logger

# Keep this list intentionally conservative. The Bot API currently allows a
# bot to set one normal reaction per message in the standard case.
_RULES: tuple[tuple[str, tuple[str, ...], str, float], ...] = (
    ("gratitude", (
        "ممنون", "مرسی", "متشکرم", "تشکر", "دمت گرم", "سپاس", "سپاسگزار",
        "thank you", "thanks", "thx", "much appreciated", "شكرا", "شكرًا", "شكراً",
        "ممتن", "ممتنة",
    ), "❤️", 0.96),
    ("praise", (
        "عالی", "خوبه", "خوب بود", "فوق العاده", "فوق‌العاده", "بی نظیر", "بی‌نظیر",
        "دمت گرم", "باحال", "خفن", "محشر", "درست گفتی", "آفرین", "احسنت",
        "great", "awesome", "excellent", "amazing", "perfect", "nice", "well done",
        "رائع", "ممتاز", "ممتازة", "رائع جدًا", "احسنت",
    ), "🔥", 0.94),
    ("celebration", (
        "تبریک", "مبارک", "هورا", "بردیم", "برد", "موفق شد", "موفقیت", "سود کردم",
        "سود گرفتم", "profit", "congrats", "congratulations", "we won", "won",
        "مبروك", "تهانينا", "نجحت", "نجاح",
    ), "🎉", 0.93),
    ("humor", (
        "😂", "🤣", "خنده دار", "خنده‌دار", "باحاله", "ترکیدم از خنده", "مردم از خنده",
        "lol", "lmao", "rofl", "haha", "هههه", "مضحك",
    ), "😂", 0.95),
    ("agreement", (
        "درسته", "حق با توئه", "موافقم", "اوکی", "باشه", "حتماً", "حتما", "قبوله",
        "درست میگی", "درست می‌گی", "exactly", "agree", "agreed", "ok", "okay", "sure",
        "صحيح", "تمام", "موافق",
    ), "👍", 0.89),
    ("sadness", (
        "ناراحتم", "غمگین", "خیلی بده", "بد شد", "متأسفم", "متاسفم", "افسوس",
        "sad", "sorry", "unfortunately", "حزين", "آسف", "للأسف",
    ), "😢", 0.87),
    ("surprise", (
        "وای", "واو", "جدی؟", "باورم نمیشه", "باورم نمی‌شه", "چی؟!", "what?!",
        "wow", "really", "no way", "مستحيل", "حقا؟", "حقًا؟",
    ), "😮", 0.86),
    ("love", (
        "دوستت دارم", "عاشقشم", "عاشقش شدم", "خیلی دوست داشتم", "خیلی دوستش دارم",
        "love it", "i love it", "love this", "so lovely", "أحب", "احب", "أحبه",
    ), "🥰", 0.91),
    ("applause", (
        "دستت درد نکنه", "دست مریزاد", "دمت گرم", "آفرین بهت", "کارت درسته",
        "well done", "bravo", "great job", "nice work", "أحسنت", "برافو", "عمل رائع",
    ), "👏", 0.92),
    ("joy", (
        "خیلی خوشحالم", "خوشحال شدم", "چه خوب", "چه عالی", "عالیه", "حال کردم",
        "happy", "so happy", "yay", "awesome", "سعيد", "سعيدة", "فرحان", "فرحانة",
    ), "😁", 0.90),
    ("excitement", (
        "هیجان انگیز", "هیجان‌انگیز", "فوق العاده بود", "عجب چیزی", "وای چه خوب",
        "exciting", "so excited", "incredible", "amazing", "مثير", "مذهل", "رائع جدًا",
    ), "🤩", 0.91),
    ("mind_blown", (
        "شوکه شدم", "شگفت زده شدم", "شگفت‌زده شدم", "باورنکردنیه", "باورنکردنی",
        "عجب", "mind blown", "mind-blowing", "unbelievable", "insane", "مذهل جدًا", "لا يصدق",
    ), "🤯", 0.90),
    ("fear", (
        "ترسیدم", "خیلی ترسناکه", "ترسناک", "وای ترس", "خطرناک به نظر میاد",
        "scary", "terrifying", "i am scared", "dangerous", "مخيف", "مرعب", "خائف",
    ), "😱", 0.88),
    ("anger", (
        "عصبانی شدم", "خیلی عصبانیم", "اعصابم خورد شد", "افتضاحه", "افتضاح بود",
        "عصبانی", "angry", "furious", "this sucks", "مزعج", "غاضب", "سيء جدًا",
    ), "🤬", 0.90),
    ("approval", (
        "صد در صد", "صددرصد", "کاملا درست", "کاملاً درست", "حرف حساب", "حرفت درسته",
        "absolutely", "100%", "one hundred percent", "totally agree", "بالتأكيد", "مئة بالمئة",
    ), "💯", 0.93),
    ("dislike", (
        "موافق نیستم", "اصلا موافق نیستم", "اصلاً موافق نیستم", "خوشم نیومد", "دوست نداشتم",
        "بد بود", "افتضاح", "i disagree", "don't like", "didn't like", "سيء", "لا أوافق",
    ), "👎", 0.88),
    ("support", (
        "نگران نباش", "امیدوارم درست بشه", "انشالله", "ان شاءالله", "موفق باشی", "خدا کنه",
        "good luck", "hopefully", "best of luck", "أتمنى", "بالتوفيق", "إن شاء الله",
    ), "🙏", 0.86),
    ("question", (
        "چطور", "چجوری", "چگونه", "چرا", "کمک میخوام", "کمک می‌خوام", "راهنمایی",
        "how do i", "how can i", "why", "help me", "كيف", "لماذا", "ساعدني",
    ), "🤔", 0.82),
)

# Cheap in-memory protection against repeated reactions after retries or
# duplicated Telegram updates. It is intentionally bounded.
_recent_messages: deque[tuple[int, int]] = deque(maxlen=4096)
_recent_set: set[tuple[int, int]] = set()
_last_by_user: dict[int, float] = {}


def _enabled() -> bool:
    return bool(getattr(config, "AUTO_REACTIONS_ENABLED", True))


def _normalize(text: str) -> str:
    value = (text or "").strip().lower()
    value = value.replace("\u200c", " ").replace("\u200f", " ").replace("\u200e", " ")
    value = re.sub(r"\s+", " ", value)
    return value


def classify_reaction(text: str) -> Optional[tuple[str, str, float]]:
    """Return (category, emoji, confidence) for a high-confidence text."""
    value = _normalize(text)
    if not value or len(value) < 3:
        return None
    max_len = max(40, int(getattr(config, "AUTO_REACTIONS_MAX_TEXT_LENGTH", 1200)))
    if len(value) > max_len:
        value = value[:max_len]

    best: Optional[tuple[str, str, float, int]] = None
    for category, phrases, emoji, confidence in _RULES:
        hits = 0
        for phrase in phrases:
            p = _normalize(phrase)
            if p in value:
                hits += 1
        if not hits:
            continue
        # A second matching phrase slightly strengthens confidence without
        # allowing long texts full of repeated keywords to dominate.
        score = min(0.995, confidence + min(0.025, (hits - 1) * 0.01))
        candidate = (category, emoji, score, hits)
        if best is None or candidate[2:] > best[2:]:
            best = candidate

    if best is None:
        return None
    category, emoji, score, _hits = best
    threshold = float(getattr(config, "AUTO_REACTIONS_MIN_CONFIDENCE", 0.80))
    if score < threshold:
        return None
    return category, emoji, score


def _scope_allows(chat_type: str | None) -> bool:
    allowed = getattr(config, "AUTO_REACTIONS_SCOPE", "private,group,supergroup")
    scopes = {x.strip().lower() for x in str(allowed).split(",") if x.strip()}
    return (chat_type or "private").lower() in scopes


def _mark_seen(key: tuple[int, int]) -> bool:
    if key in _recent_set:
        return False
    if len(_recent_messages) == _recent_messages.maxlen:
        old = _recent_messages[0]
        _recent_set.discard(old)
    _recent_messages.append(key)
    _recent_set.add(key)
    return True


async def _set_reaction(token: str, chat_id: int | str, message_id: int, emoji: str) -> bool:
    url = f"https://api.telegram.org/bot{token}/setMessageReaction"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "reaction": [{"type": "emoji", "emoji": emoji}],
        "is_big": bool(getattr(config, "AUTO_REACTIONS_BIG", False)),
    }
    timeout = float(getattr(config, "AUTO_REACTIONS_TIMEOUT", 4.0))
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload)
        if response.status_code != 200:
            logger.debug("auto reaction HTTP %s: %s", response.status_code, response.text[:240])
            return False
        data = response.json()
        if not data.get("ok"):
            logger.debug("auto reaction rejected: %s", str(data)[:300])
            return False
        return True
    except Exception as exc:
        # Reactions are optional UX; never break the user's main message flow.
        logger.debug("auto reaction failed: %s", exc)
        return False


async def maybe_auto_react(update, context) -> bool:
    """React to an incoming user message when a configured rule matches."""
    if not _enabled() or not update or not update.message:
        return False
    message = update.message
    if not message.text or getattr(message, "from_user", None) is None:
        return False
    if getattr(message.from_user, "is_bot", False):
        return False
    if not _scope_allows(getattr(update.effective_chat, "type", None)):
        return False

    result = classify_reaction(message.text)
    if result is None:
        return False
    _category, emoji, _confidence = result

    user_id = int(message.from_user.id)
    now = time.monotonic()
    cooldown = max(0.0, float(getattr(config, "AUTO_REACTIONS_COOLDOWN", 8.0)))
    if now - _last_by_user.get(user_id, 0.0) < cooldown:
        return False

    key = (int(update.effective_chat.id), int(message.message_id))
    if not _mark_seen(key):
        return False

    token = (getattr(config, "BOT_TOKEN", "") or "").strip()
    if not token:
        return False
    ok = await _set_reaction(token, update.effective_chat.id, message.message_id, emoji)
    if ok:
        _last_by_user[user_id] = now
        # Bound user timestamps in long-running processes.
        if len(_last_by_user) > 4096:
            cutoff = now - max(cooldown, 60.0) * 2
            stale = [uid for uid, ts in _last_by_user.items() if ts < cutoff]
            for uid in stale[:2048]:
                _last_by_user.pop(uid, None)
        logger.debug("auto reaction: user=%s category=%s emoji=%s", user_id, _category, emoji)
    return ok
