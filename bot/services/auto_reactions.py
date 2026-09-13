"""Reliable automatic Telegram reactions for incoming user messages."""
from __future__ import annotations

import json
import re
import time
from collections import deque
from typing import Optional

import httpx

from bot.config import config
from bot.logger import logger

# category, phrases, emoji, confidence
_RULES: tuple[tuple[str, tuple[str, ...], str, float], ...] = (
    ("gratitude", ("ممنون", "مرسی", "متشکرم", "تشکر", "دمت گرم", "سپاس", "سپاسگزار", "thank you", "thanks", "thx", "شكرا", "شكرًا", "شكراً"), "❤️", .96),
    ("praise", ("عالی", "خوبه", "خوب بود", "فوق العاده", "فوق‌العاده", "بی نظیر", "بی‌نظیر", "باحال", "خفن", "محشر", "درست گفتی", "آفرین", "احسنت", "great", "awesome", "excellent", "amazing", "perfect", "رائع", "ممتاز"), "🔥", .94),
    ("celebration", ("تبریک", "مبارک", "هورا", "بردیم", "موفق شد", "موفقیت", "سود کردم", "سود گرفتم", "profit", "congrats", "congratulations", "مبروك", "تهانينا", "نجحت", "نجاح"), "🎉", .93),
    ("humor", ("😂", "🤣", "خنده دار", "خنده‌دار", "ترکیدم از خنده", "مردم از خنده", "lol", "lmao", "rofl", "haha", "هههه", "مضحك"), "😂", .95),
    ("agreement", ("درسته", "حق با توئه", "موافقم", "اوکی", "باشه", "حتماً", "حتما", "قبوله", "درست میگی", "درست می‌گی", "exactly", "agree", "agreed", "ok", "okay", "sure", "صحيح", "تمام", "موافق"), "👍", .89),
    ("sadness", ("ناراحتم", "غمگین", "خیلی بده", "بد شد", "متأسفم", "متاسفم", "افسوس", "sad", "sorry", "unfortunately", "حزين", "آسف", "للأسف"), "😢", .87),
    ("surprise", ("وای", "واو", "جدی؟", "باورم نمیشه", "باورم نمی‌شه", "چی؟!", "what?!", "wow", "really", "no way", "مستحيل", "حقا؟", "حقًا؟"), "😮", .86),
    ("love", ("دوستت دارم", "عاشقشم", "عاشقش شدم", "خیلی دوست داشتم", "خیلی دوستش دارم", "خیلی دوست دارم", "love it", "i love it", "love this", "so lovely", "أحب", "احب", "أحبه"), "🥰", .91),
    ("applause", ("دستت درد نکنه", "دست مریزاد", "آفرین بهت", "کارت درسته", "well done", "bravo", "great job", "nice work", "أحسنت", "برافو", "عمل رائع"), "👏", .92),
    ("joy", ("خیلی خوشحالم", "خوشحال شدم", "چه خوب", "چه عالی", "عالیه", "حال کردم", "happy", "so happy", "yay", "سعيد", "سعيدة", "فرحان", "فرحانة"), "😁", .90),
    ("excitement", ("هیجان انگیز", "هیجان‌انگیز", "فوق العاده بود", "عجب چیزی", "وای چه خوب", "exciting", "so excited", "incredible", "مثير", "مذهل", "رائع جدًا"), "🤩", .91),
    ("mind_blown", ("شوکه شدم", "شگفت زده شدم", "شگفت‌زده شدم", "باورنکردنیه", "باورنکردنی", "عجب", "mind blown", "mind-blowing", "unbelievable", "insane", "مذهل جدًا", "لا يصدق"), "🤯", .90),
    ("fear", ("ترسیدم", "خیلی ترسناکه", "ترسناک", "وای ترس", "خطرناک به نظر میاد", "scary", "terrifying", "i am scared", "dangerous", "مخيف", "مرعب", "خائف"), "😱", .88),
    ("anger", ("عصبانی شدم", "خیلی عصبانیم", "اعصابم خورد شد", "افتضاحه", "افتضاح بود", "عصبانی", "angry", "furious", "this sucks", "مزعج", "غاضب", "سيء جدًا"), "🤬", .90),
    ("approval", ("صد در صد", "صددرصد", "کاملا درست", "کاملاً درست", "حرف حساب", "حرفت درسته", "absolutely", "100%", "one hundred percent", "totally agree", "بالتأكيد", "مئة بالمئة"), "💯", .93),
    ("dislike", ("موافق نیستم", "اصلا موافق نیستم", "اصلاً موافق نیستم", "خوشم نیومد", "دوست نداشتم", "بد بود", "افتضاح", "i disagree", "don't like", "didn't like", "سيء", "لا أوافق"), "👎", .88),
    ("support", ("نگران نباش", "امیدوارم درست بشه", "انشالله", "ان شاءالله", "موفق باشی", "خدا کنه", "good luck", "hopefully", "best of luck", "أتمنى", "بالتوفيق", "إن شاء الله"), "🙏", .86),
    ("question", ("چطور", "چجوری", "چگونه", "چرا", "کمک میخوام", "کمک می‌خوام", "راهنمایی", "how do i", "how can i", "why", "help me", "كيف", "لماذا", "ساعدني"), "🤔", .82),
)

_recent_messages: deque[tuple[int, int]] = deque(maxlen=4096)
_recent_set: set[tuple[int, int]] = set()
_last_by_user: dict[int, float] = {}
_available_cache: dict[int, tuple[float, Optional[set[str]]]] = {}


def _enabled() -> bool:
    return bool(getattr(config, "AUTO_REACTIONS_ENABLED", True))


def _normalize(text: str) -> str:
    value = (text or "").strip().lower()
    value = value.replace("\u200c", " ").replace("\u200f", " ").replace("\u200e", " ")
    return re.sub(r"\s+", " ", value)


def classify_reaction(text: str) -> Optional[tuple[str, str, float]]:
    value = _normalize(text)
    if not value or len(value) < 3:
        return None
    max_len = max(40, int(getattr(config, "AUTO_REACTIONS_MAX_TEXT_LENGTH", 1200)))
    value = value[:max_len]
    best = None
    for category, phrases, emoji, confidence in _RULES:
        hits = sum(1 for phrase in phrases if _normalize(phrase) in value)
        if hits:
            score = min(.995, confidence + min(.025, (hits - 1) * .01))
            candidate = (category, emoji, score, hits)
            if best is None or candidate[2:] > best[2:]:
                best = candidate
    if best is None:
        return None
    category, emoji, score, _ = best
    if score < float(getattr(config, "AUTO_REACTIONS_MIN_CONFIDENCE", .80)):
        return None
    return category, emoji, score


def _scope_allows(chat_type: str | None) -> bool:
    allowed = getattr(config, "AUTO_REACTIONS_SCOPE", "private,group,supergroup")
    return (chat_type or "private").lower() in {x.strip().lower() for x in str(allowed).split(",") if x.strip()}


def _mark_seen(key: tuple[int, int]) -> bool:
    if key in _recent_set:
        return False
    if len(_recent_messages) == _recent_messages.maxlen:
        _recent_set.discard(_recent_messages[0])
    _recent_messages.append(key)
    _recent_set.add(key)
    return True


async def _api(token: str, method: str, data: dict, timeout: float) -> tuple[bool, dict]:
    url = f"https://api.telegram.org/bot{token}/{method}"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            # Bot API accepts standard form encoding; this also avoids clients/proxies
            # mishandling a nested JSON field when json= is used.
            response = await client.post(url, data=data)
        try:
            payload = response.json()
        except Exception:
            payload = {"ok": False, "description": response.text[:300]}
        return response.status_code == 200 and bool(payload.get("ok")), payload
    except Exception as exc:
        return False, {"ok": False, "description": str(exc)}


async def _available_reactions(token: str, chat_id: int | str, timeout: float) -> Optional[set[str]]:
    """Return explicitly allowed emoji reactions, or None when Telegram says unrestricted."""
    try:
        cid = int(chat_id)
    except (TypeError, ValueError):
        return None
    now = time.monotonic()
    cached = _available_cache.get(cid)
    ttl = float(getattr(config, "AUTO_REACTIONS_CHAT_CACHE_TTL", 600.0))
    if cached and now - cached[0] < ttl:
        return cached[1]
    ok, payload = await _api(token, "getChat", {"chat_id": chat_id}, timeout)
    if not ok:
        # Failure to inspect chat settings must not disable reactions entirely.
        return None
    chat = payload.get("result") or {}
    raw = chat.get("available_reactions")
    if raw is None:
        allowed = None
    else:
        allowed = {str(item.get("emoji")) for item in raw if isinstance(item, dict) and item.get("type") == "emoji" and item.get("emoji")}
    _available_cache[cid] = (now, allowed)
    return allowed


async def _set_reaction(token: str, chat_id: int | str, message_id: int, emoji: str) -> bool:
    timeout = float(getattr(config, "AUTO_REACTIONS_TIMEOUT", 5.0))
    allowed = await _available_reactions(token, chat_id, timeout)
    if allowed is not None and emoji not in allowed:
        # Pick a semantically neutral reaction that Telegram explicitly permits.
        for fallback in ("❤️", "👍", "🔥", "👏", "😂"):
            if fallback in allowed:
                emoji = fallback
                break
        else:
            logger.info("auto reaction skipped: no compatible emoji reaction allowed in chat=%s", chat_id)
            return False

    reaction_json = json.dumps([{"type": "emoji", "emoji": emoji}], ensure_ascii=False)
    ok, payload = await _api(token, "setMessageReaction", {
        "chat_id": chat_id,
        "message_id": message_id,
        "reaction": reaction_json,
        "is_big": "true" if bool(getattr(config, "AUTO_REACTIONS_BIG", False)) else "false",
    }, timeout)
    if ok:
        return True

    description = str(payload.get("description", "unknown Telegram error"))
    # If a cached allowed list became stale, refresh once and retry with the same
    # semantic emoji or a currently allowed fallback.
    if "REACTION_INVALID" in description or "reaction" in description.lower():
        _available_cache.pop(int(chat_id), None) if str(chat_id).lstrip("-").isdigit() else None
        allowed = await _available_reactions(token, chat_id, timeout)
        if allowed is not None:
            candidate = emoji if emoji in allowed else next((x for x in ("❤️", "👍", "🔥", "👏", "😂") if x in allowed), None)
            if candidate:
                ok2, payload2 = await _api(token, "setMessageReaction", {
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "reaction": json.dumps([{"type": "emoji", "emoji": candidate}], ensure_ascii=False),
                    "is_big": "false",
                }, timeout)
                if ok2:
                    return True
                description = str(payload2.get("description", description))
    logger.warning("auto reaction failed chat=%s message=%s emoji=%s: %s", chat_id, message_id, emoji, description[:300])
    return False


async def maybe_auto_react(update, context=None) -> bool:
    if not _enabled() or not update or not getattr(update, "message", None):
        return False
    message = update.message
    if not getattr(message, "text", None) or getattr(message, "from_user", None) is None:
        return False
    if getattr(message.from_user, "is_bot", False):
        return False
    chat = getattr(update, "effective_chat", None)
    if not chat or not _scope_allows(getattr(chat, "type", None)):
        return False
    result = classify_reaction(message.text)
    if result is None:
        return False
    category, emoji, confidence = result
    user_id = int(message.from_user.id)
    now = time.monotonic()
    cooldown = max(0.0, float(getattr(config, "AUTO_REACTIONS_COOLDOWN", 3.0)))
    if now - _last_by_user.get(user_id, 0.0) < cooldown:
        return False
    key = (int(chat.id), int(message.message_id))
    if not _mark_seen(key):
        return False
    token = (getattr(config, "BOT_TOKEN", "") or "").strip()
    if not token:
        return False
    ok = await _set_reaction(token, chat.id, message.message_id, emoji)
    if ok:
        _last_by_user[user_id] = now
        logger.info("auto reaction applied user=%s chat=%s message=%s category=%s emoji=%s confidence=%.2f", user_id, chat.id, message.message_id, category, emoji, confidence)
    return ok
