"""Reliable automatic Telegram reactions for incoming user messages."""
from __future__ import annotations
from bot.utils.modular_loader import load_modular_part

import asyncio
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
_queue: Optional[asyncio.Queue] = None
_worker_task: Optional[asyncio.Task] = None
_client: Optional[httpx.AsyncClient] = None


load_modular_part(__file__, 'auto_reactions_parts/part_001__enabled.py')


load_modular_part(__file__, 'auto_reactions_parts/part_002__normalize.py')


load_modular_part(__file__, 'auto_reactions_parts/part_003_classify_reaction.py')


load_modular_part(__file__, 'auto_reactions_parts/part_004__scope_allows.py')


load_modular_part(__file__, 'auto_reactions_parts/part_005__mark_seen.py')


load_modular_part(__file__, 'auto_reactions_parts/part_006__get_client.py')


load_modular_part(__file__, 'auto_reactions_parts/part_007__api.py')


load_modular_part(__file__, 'auto_reactions_parts/part_008__available_reactions.py')


load_modular_part(__file__, 'auto_reactions_parts/part_009__set_reaction.py')


load_modular_part(__file__, 'auto_reactions_parts/part_010__worker.py')


load_modular_part(__file__, 'auto_reactions_parts/part_011__ensure_worker.py')


load_modular_part(__file__, 'auto_reactions_parts/part_012_enqueue_auto_reaction.py')


load_modular_part(__file__, 'auto_reactions_parts/part_013_maybe_auto_react.py')
