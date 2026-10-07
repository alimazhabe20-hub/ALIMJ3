"""Telegram UX enhancements: pagination, smart actions, alerts and inline mode.

This module is deliberately isolated from the large legacy handlers.  It keeps
callback payloads short, edits existing messages whenever possible, and uses the
existing V61/V65 price-alert storage/scheduler instead of creating a second alert
system.
"""
from __future__ import annotations

import asyncio
import html
import re
import time
import uuid
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent, Update
from telegram.ext import ContextTypes


_PAGE_TTL = 3600
_MAX_PAGE_STORE = 128
_GLOBAL_PAGES: dict[str, Any] = {}


def split_text(text: str, limit: int = 3900) -> list[str]:
    raw = (text or "").strip()
    if not raw:
        return []
    out: list[str] = []
    current = ""
    for line in raw.splitlines():
        candidate = line if not current else current + "\n" + line
        if len(candidate) <= limit:
            current = candidate
            continue
        if current:
            out.append(current)
            current = ""
        rest = line
        while len(rest) > limit:
            cut = rest.rfind(" ", 0, limit + 1)
            if cut < limit // 2:
                cut = limit
            out.append(rest[:cut].rstrip())
            rest = rest[cut:].lstrip()
        current = rest
    if current:
        out.append(current)
    return out


def _cleanup_pages(store: dict[str, Any]) -> None:
    now = time.time()
    dead = [k for k, v in store.items() if float(v.get("expires", 0)) < now]
    for k in dead:
        store.pop(k, None)
    while len(store) > _MAX_PAGE_STORE:
        store.pop(next(iter(store)))


def save_pages(context: ContextTypes.DEFAULT_TYPE | None, pages: list[str], *, prompt: str = "") -> str:
    store = context.user_data.setdefault("_tg_pages", {}) if context is not None else _GLOBAL_PAGES
    _cleanup_pages(store)
    token = uuid.uuid4().hex[:10]
    item = {"pages": pages, "expires": time.time() + _PAGE_TTL, "prompt": prompt or ""}
    store[token] = item
    _GLOBAL_PAGES[token] = item
    return token


def pagination_keyboard(token: str, index: int, total: int, *, smart: bool = True) -> InlineKeyboardMarkup:
    nav: list[InlineKeyboardButton] = []
    if index > 0:
        nav.append(InlineKeyboardButton("◀️ قبلی", callback_data=f"enh:p:{token}:{index-1}"))
    nav.append(InlineKeyboardButton(f"{index+1}/{total}", callback_data="enh:nop"))
    if index < total - 1:
        nav.append(InlineKeyboardButton("بعدی ▶️", callback_data=f"enh:p:{token}:{index+1}"))
    rows = [nav]
    if smart:
        rows.append([
            InlineKeyboardButton("🔄 پاسخ دوباره", callback_data=f"enh:refresh:{token}"),
            InlineKeyboardButton("▶️ ادامه", callback_data=f"enh:continue:{token}"),
        ])
    return InlineKeyboardMarkup(rows)


async def send_paginated(message, context: ContextTypes.DEFAULT_TYPE, text: str, *, prompt: str = "", prefix: str = "🤖 "):
    pages = split_text(prefix + (text or "")) or [prefix + "پاسخی دریافت نشد."]
    if len(pages) == 1:
        return await message.reply_text(pages[0])
    token = save_pages(context, pages, prompt=prompt)
    return await message.reply_text(pages[0], reply_markup=pagination_keyboard(token, 0, len(pages)))


def smart_action_keyboard(text: str, *, answer_id: str = "") -> InlineKeyboardMarkup | None:
    s = (text or "").lower()
    rows: list[list[InlineKeyboardButton]] = []
    if re.search(r"(?:btc|bitcoin|بیت.?کوین|eth|ethereum|اتریوم|sol|سولانا|xau|gold|طلا)", s, re.I):
        rows.append([
            InlineKeyboardButton("🔔 هشدار قیمت", callback_data="enh:alert"),
            InlineKeyboardButton("📊 تحلیل مجدد", callback_data="enh:retry_market"),
        ])
    elif re.search(r"(?:خرید|قیمت|فروشگاه|دیجی.?کالا|ترب|shop|product|محصول)", s, re.I):
        rows.append([
            InlineKeyboardButton("🔎 جستجوی بیشتر", callback_data="enh:shop_more"),
            InlineKeyboardButton("💰 مقایسه قیمت", callback_data="enh:shop_compare"),
        ])
    elif re.search(r"(?:هوا|آب.?و.?هوا|weather|دما)", s, re.I):
        rows.append([InlineKeyboardButton("🌤 بروزرسانی", callback_data="enh:weather_refresh")])
    if answer_id:
        rows.append([InlineKeyboardButton("📋 کپی پاسخ", callback_data=f"enh:copy:{answer_id}")])
    return InlineKeyboardMarkup(rows) if rows else None


async def enhancement_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q:
        return
    data = q.data or ""
    try:
        await q.answer()
    except Exception:
        pass

    if data == "enh:nop":
        return

    if data.startswith("enh:p:"):
        _, _, token, idx = data.split(":", 3)
        store = context.user_data.get("_tg_pages", {})
        item = store.get(token) or _GLOBAL_PAGES.get(token)
        if not item or item.get("expires", 0) < time.time():
            await q.answer("این صفحه منقضی شده؛ دوباره درخواست بدهید.", show_alert=True)
            return
        pages = item["pages"]
        index = max(0, min(int(idx), len(pages) - 1))
        await q.edit_message_text(pages[index], reply_markup=pagination_keyboard(token, index, len(pages)))
        return

    if data.startswith("enh:copy:"):
        aid = data.split(":", 2)[2]
        from bot.services.ai_extras import get_stored_answer
        answer = get_stored_answer(aid, q.from_user.id) or ""
        if not answer:
            await q.answer("پاسخ منقضی شده است.", show_alert=True)
            return
        # Telegram has no universal bot-side clipboard write API; send copyable text.
        await q.message.reply_text(answer[:4000])
        return

    if data == "enh:alert":
        await q.message.reply_text(
            "🔔 ساخت هشدار قیمت\n\n"
            "فرمت:\n"
            "`/alerts add BTC 90000 above`\n\n"
            "مثال پایین‌تر:\n"
            "`/alerts add BTC 80000 below`",
            parse_mode="Markdown",
        )
        return

    if data in {"enh:retry_market", "enh:shop_more", "enh:shop_compare", "enh:weather_refresh"}:
        # Keep the action explicit instead of guessing a hidden query.
        prompts = {
            "enh:retry_market": "همین موضوع را با داده زنده دوباره تحلیل کن و فقط نتیجه جدید را بده.",
            "enh:shop_more": "برای همان محصول، جستجوی خرید زنده را گسترده‌تر کن و چند فروشگاه بیشتر با قیمت و لینک مستقیم بده.",
            "enh:shop_compare": "برای همان محصول، مقایسه قیمت زنده بین فروشگاه‌ها را انجام بده.",
            "enh:weather_refresh": "آب‌وهوای همین شهر را با داده زنده دوباره بررسی کن.",
        }
        from bot.services.ai_service import ask_ai
        try:
            answer, provider = await ask_ai(q.from_user.id, prompts[data])
            await q.message.reply_text((answer or "نتیجه‌ای برنگشت.")[:4000])
        except Exception as exc:
            await q.message.reply_text("⚠️ اجرای دوباره ناموفق بود؛ چند لحظه بعد تلاش کنید.")
        return

    if data.startswith("enh:continue:") or data.startswith("enh:refresh:"):
        token = data.split(":", 2)[2]
        item = context.user_data.get("_tg_pages", {}).get(token) or _GLOBAL_PAGES.get(token)
        prompt = (item or {}).get("prompt") or ""
        from bot.services.ai_service import ask_ai
        if data.startswith("enh:continue:"):
            request = "پاسخ قبلی را دقیقاً از همان‌جایی که تمام شد ادامه بده؛ تکرار نکن."
        else:
            request = prompt or "پاسخ قبلی را با همان موضوع، از نو و دقیق‌تر پاسخ بده."
        try:
            answer, _ = await ask_ai(q.from_user.id, request)
            await q.message.reply_text((answer or "نتیجه‌ای برنگشت.")[:4000])
        except Exception:
            await q.message.reply_text("⚠️ اجرای AI ناموفق بود.")


async def inline_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inline mode: product/web/AI answer cards usable in any Telegram chat."""
    query = (update.inline_query.query or "").strip()
    if not query:
        results = [InlineQueryResultArticle(
            id="help",
            title="🤖 روز زیبا",
            description="جستجو، خرید، قیمت و پاسخ AI",
            input_message_content=InputTextMessageContent("برای جستجو بنویس: @YOUR_BOT محصول یا سؤال"),
        )]
        await update.inline_query.answer(results, cache_time=2, is_personal=True)
        return

    results: list[InlineQueryResultArticle] = []
    try:
        if re.search(r"(?:خرید|قیمت|محصول|فروشگاه|دیجی.?کالا|ترب|shop|product)", query, re.I):
            from bot.features.market.shopping import search_shopping
            raw = await asyncio.wait_for(search_shopping(query, max_results=6, user_id=update.inline_query.from_user.id), timeout=12)
            text = str(raw or "نتیجه خریدی پیدا نشد.")[:3900]
            results.append(InlineQueryResultArticle(
                id="shop-" + uuid.uuid4().hex[:8],
                title="🛒 نتیجه خرید",
                description=query[:100],
                input_message_content=InputTextMessageContent(text),
            ))
        else:
            from bot.services.ai_service import ask_ai
            answer, _ = await asyncio.wait_for(ask_ai(update.inline_query.from_user.id, query), timeout=15)
            results.append(InlineQueryResultArticle(
                id="ai-" + uuid.uuid4().hex[:8],
                title="🤖 پاسخ AI",
                description=(answer or "")[:160],
                input_message_content=InputTextMessageContent((answer or "نتیجه‌ای برنگشت.")[:4000]),
            ))
    except Exception:
        results = [InlineQueryResultArticle(
            id="fallback-" + uuid.uuid4().hex[:8],
            title="⚠️ نتیجه موقتاً در دسترس نیست",
            description="دوباره تلاش کنید",
            input_message_content=InputTextMessageContent("⚠️ سرویس inline موقتاً پاسخ نداد."),
        )]
    await update.inline_query.answer(results, cache_time=3, is_personal=True)


# AI tools: smart price alerts reuse the existing V65 persistence and 60-second scheduler.
def register_smart_alert_tools(register_tool):
    async def create_price_alert(symbol: str, target: float, direction: str = "above", user_id: int = 0) -> str:
        from bot.services.v61_v65_platform import add_alert
        d = str(direction or "above").lower()
        if d in {"پایین", "زیر", "below", "down"}:
            d = "below"
        else:
            d = "above"
        aid = add_alert(int(user_id), str(symbol).upper(), float(target), d)
        return f"🔔 هشدار ثبت شد: {str(symbol).upper()} {d} {float(target):g} | ID={aid}"

    def list_price_alerts(user_id: int = 0) -> str:
        from bot.services.v61_v65_platform import get_alerts
        rows = get_alerts(int(user_id))
        if not rows:
            return "🔔 هشدار فعالی ندارید."
        return "\n".join(f"#{r[0]} • {r[1]} {r[3]} {r[2]}" for r in rows[:50])

    def remove_price_alert(alert_id: int, user_id: int = 0) -> str:
        from bot.services.v61_v65_platform import remove_alert
        return "✅ هشدار حذف شد." if remove_alert(int(user_id), int(alert_id)) else "⚠️ هشدار پیدا نشد."

    register_tool(
        name="create_price_alert",
        description="ثبت هشدار قیمت واقعی و پایدار؛ Scheduler موجود ربات آن را بررسی و در صورت رسیدن قیمت پیام می‌فرستد.",
        parameters={"type":"object","properties":{"symbol":{"type":"string"},"target":{"type":"number"},"direction":{"type":"string","enum":["above","below"]}},"required":["symbol","target"]},
        handler=create_price_alert,
        keywords=[r"هشدار.*(?:قیمت|برسد|رسید)", r"alert.*price", r"price alert"],
        risk="write",
    )
    register_tool(
        name="list_price_alerts",
        description="نمایش هشدارهای قیمت فعال کاربر.",
        parameters={"type":"object","properties":{}}, handler=list_price_alerts,
        keywords=[r"هشدارهای? من", r"لیست هشدار", r"my alerts"], risk="read",
    )
    register_tool(
        name="remove_price_alert",
        description="حذف یک هشدار قیمت فعال با شناسه.",
        parameters={"type":"object","properties":{"alert_id":{"type":"integer"}},"required":["alert_id"]}, handler=remove_price_alert,
        keywords=[r"حذف هشدار", r"remove alert"], risk="write",
    )
