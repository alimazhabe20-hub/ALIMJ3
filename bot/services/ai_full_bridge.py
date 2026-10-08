"""Bridge: wire every remaining bot capability into the AI tool registry.

This module is loaded by ``capability_autoload.ensure_all_capabilities_registered``.
It does not re-implement business logic — it only adapts existing feature /
database / service functions into AI tools.

When you add a *new* feature later, prefer::

    from bot.services.capability_autoload import ai_tool

    @ai_tool(name="...", description="...", parameters={...}, keywords=[...])
    def my_new_feature(...):
        ...

so it is picked up automatically without editing this bridge.
"""

import logging
from typing import Any

logger = logging.getLogger("rooze_ziba")
_REGISTERED = False


def _safe(fn, *args, **kwargs) -> str:
    try:
        out = fn(*args, **kwargs)
        if out is None:
            return "انجام شد."
        return str(out)
    except Exception as exc:
        logger.warning("ai_full_bridge %s failed: %s", getattr(fn, "__name__", fn), exc)
        return f"⚠️ خطا در اجرای قابلیت: {exc}"


async def _safe_async(fn, *args, **kwargs) -> str:
    try:
        out = await fn(*args, **kwargs)
        if out is None:
            return "انجام شد."
        return str(out)
    except Exception as exc:
        logger.warning("ai_full_bridge async %s failed: %s", getattr(fn, "__name__", fn), exc)
        return f"⚠️ خطا در اجرای قابلیت: {exc}"


# ── handlers ───────────────────────────────────────────────────────────────

def _profit_loss(buy: float = 0, sell: float = 0, qty: float = 1) -> str:
    from bot.features.market.finance import profit_loss
    return _safe(profit_loss, float(buy), float(sell), float(qty or 1))


async def _analyze_gold(timeframe: str = "4h") -> str:
    from bot.features.market.finance import analyze_gold
    return await _safe_async(analyze_gold, timeframe or "4h")


def _date_diff(
    date1: str = "",
    date2: str = "",
    y1: int = 0, m1: int = 0, d1: int = 0,
    y2: int = 0, m2: int = 0, d2: int = 0,
) -> str:
    from bot.features.date.features_date_date_tools import date_diff, parse_shamsi

    def _parse(text: str, y: int, m: int, d: int):
        if y and m and d:
            return int(y), int(m), int(d)
        p = parse_shamsi(text or "")
        if not p:
            return None
        return int(p[0]), int(p[1]), int(p[2])

    a = _parse(date1, y1, m1, d1)
    b = _parse(date2, y2, m2, d2)
    if not a or not b:
        return "تاریخ نامعتبر. مثال: 1400/01/01 و 1403/07/15"
    return _safe(date_diff, a[0], a[1], a[2], b[0], b[1], b[2])


def _age_diff(
    birth1: str = "",
    birth2: str = "",
    y1: int = 0, m1: int = 0, d1: int = 0,
    y2: int = 0, m2: int = 0, d2: int = 0,
) -> str:
    from bot.features.date.features_date_date_tools import age_diff, parse_shamsi

    def _parse(text: str, y: int, m: int, d: int):
        if y and m and d:
            return int(y), int(m), int(d)
        p = parse_shamsi(text or "")
        if not p:
            return None
        return int(p[0]), int(p[1]), int(p[2])

    a = _parse(birth1, y1, m1, d1)
    b = _parse(birth2, y2, m2, d2)
    if not a or not b:
        return "تاریخ تولد نامعتبر. مثال: 1370/05/12 و 1375/01/01"
    return _safe(age_diff, a[0], a[1], a[2], b[0], b[1], b[2])


def _custom_countdown(text: str = "") -> str:
    from bot.features.date.features_date_date_tools import parse_countdown
    try:
        from bot.features.date.features_date_date_tools import custom_countdown
    except Exception:
        custom_countdown = None
    parsed = parse_countdown(text or "")
    if not parsed:
        return "نتوانستم تاریخ هدف را بفهمم. مثال: تا 1405/01/01 نوروز"
    y, m, d, label = parsed
    if custom_countdown:
        return _safe(custom_countdown, y, m, d, label)
    # Fallback minimal
    import jdatetime
    from datetime import date
    target = jdatetime.date(int(y), int(m), int(d)).togregorian()
    delta = (target - date.today()).days
    if delta >= 0:
        return f"⏳ شمارش‌معکوس: {label}\n{delta} روز مانده\n📅 {y}/{m:02d}/{d:02d}"
    return f"⏳ {label}: {-delta} روز پیش بوده است\n📅 {y}/{m:02d}/{d:02d}"


def _list_reminders(user_id: int = 0, limit: int = 15) -> str:
    from bot.database import list_user_reminders
    rows = list_user_reminders(user_id, int(limit or 15)) or []
    if not rows:
        return "یادآوری فعالی ندارید."
    lines = ["⏰ یادآوری‌های شما:"]
    for r in rows:
        rid, text, when, rep, every, done, active = r[:7]
        status = "✅" if not done and active else "✔️ انجام/لغو"
        lines.append(f"#{rid} {status} — {text} @ {when} ({rep})")
    return "\n".join(lines)


def _cancel_reminder(user_id: int = 0, reminder_id: int = 0) -> str:
    from bot.database import cancel_reminder
    ok = cancel_reminder(user_id, int(reminder_id))
    return "✅ یادآوری لغو شد." if ok else "یادآوری پیدا نشد."


def _add_note(user_id: int = 0, content: str = "") -> str:
    content = (content or "").strip()
    if not content:
        return "متن یادداشت خالی است."
    from bot.database import add_note
    add_note(user_id, content)
    return f"✅ یادداشت ذخیره شد: {content[:200]}"


def _list_notes(user_id: int = 0, limit: int = 10) -> str:
    from bot.database import get_notes
    rows = get_notes(user_id, int(limit or 10)) or []
    if not rows:
        return "یادداشتی ندارید."
    lines = ["📒 یادداشت‌های شما:"]
    for nid, content, created in rows:
        lines.append(f"#{nid} ({created}): {content}")
    return "\n".join(lines)


def _delete_note(user_id: int = 0, note_id: int = 0) -> str:
    from bot.database import delete_note
    delete_note(user_id, int(note_id))
    return f"✅ یادداشت #{note_id} حذف شد."


def _save_birth_date(user_id: int = 0, birth_date: str = "") -> str:
    birth_date = (birth_date or "").strip()
    if not birth_date:
        return "تاریخ تولد را بفرست. مثال: 1375/03/15"
    try:
        from bot.database import set_birth_date
        set_birth_date(user_id, birth_date)
        return f"✅ تاریخ تولد ذخیره شد: {birth_date}"
    except Exception as exc:
        # fallback via update_user_field
        try:
            from bot.database import update_user_field
            update_user_field(user_id, "birth_date", birth_date)
            return f"✅ تاریخ تولد ذخیره شد: {birth_date}"
        except Exception:
            return f"⚠️ ذخیره تاریخ تولد ممکن نشد: {exc}"


def _user_stats(user_id: int = 0) -> str:
    try:
        from bot.database import get_user_usage, get_user_city, get_birth_date
        city = get_user_city(user_id) or "—"
        birth = get_birth_date(user_id) or "—"
        usage = get_user_usage(user_id) or []
        lines = [f"📊 آمار شما", f"شهر: {city}", f"تاریخ تولد: {birth}", ""]
        if usage:
            lines.append("استفاده از قابلیت‌ها:")
            for row in usage[:20]:
                lines.append(f"• {row}")
        else:
            lines.append("هنوز آمار ثبت‌شده‌ای نیست.")
        return "\n".join(lines)
    except Exception as exc:
        return f"⚠️ آمار در دسترس نیست: {exc}"


def _set_user_city(user_id: int = 0, city: str = "") -> str:
    city = (city or "").strip()
    if not city:
        return "نام شهر را بفرست."
    from bot.database import update_user_field
    update_user_field(user_id, "city", city)
    return f"✅ شهر شما → {city}"


def _set_user_language(user_id: int = 0, language: str = "fa") -> str:
    language = (language or "fa").strip().lower()
    if language in {"فارسی", "persian", "farsi"}:
        language = "fa"
    elif language in {"english", "en", "انگلیسی"}:
        language = "en"
    elif language in {"arabic", "ar", "عربی"}:
        language = "ar"
    if language not in {"fa", "en", "ar"}:
        return "زبان معتبر: fa / en / ar"
    from bot.database import update_user_field
    update_user_field(user_id, "language", language)
    return f"✅ زبان → {language}"


def _get_azan_settings(user_id: int = 0) -> str:
    from bot.database import get_azan_settings
    s = get_azan_settings(user_id) or {}
    if not s:
        return "تنظیمات اذان یافت نشد."
    def mark(k):
        return "✅" if s.get(k) else "❌"
    return (
        f"🔔 تنظیمات اذان\n"
        f"اعلان‌ها: {'روشن' if s.get('enabled') else 'خاموش'}\n"
        f"{mark('fajr')} صبح  {mark('dhuhr')} ظهر  {mark('asr')} عصر\n"
        f"{mark('maghrib')} مغرب  {mark('isha')} عشاء"
    )


def _set_azan(
    user_id: int = 0,
    enabled: str = "",
    prayer: str = "",
    on: str = "",
) -> str:
    """enabled=on/off for master; or prayer=fajr|dhuhr|asr|maghrib|isha and on=on/off."""
    try:
        from bot.database import set_azan_master, toggle_azan_prayer, get_azan_settings
    except Exception as exc:
        return f"⚠️ تنظیم اذان در دسترس نیست: {exc}"

    enabled_l = (enabled or "").strip().lower()
    if enabled_l in {"on", "1", "true", "روشن", "yes"}:
        set_azan_master(user_id, True)
        return "✅ اعلان اذان روشن شد.\n" + _get_azan_settings(user_id)
    if enabled_l in {"off", "0", "false", "خاموش", "no"}:
        set_azan_master(user_id, False)
        return "🔕 اعلان اذان خاموش شد.\n" + _get_azan_settings(user_id)

    prayer = (prayer or "").strip().lower()
    mapping = {
        "fajr": "fajr", "صبح": "fajr", "اذان صبح": "fajr",
        "dhuhr": "dhuhr", "ظهر": "dhuhr",
        "asr": "asr", "عصر": "asr",
        "maghrib": "maghrib", "مغرب": "maghrib",
        "isha": "isha", "عشاء": "isha",
    }
    key = mapping.get(prayer)
    if not key:
        return "نماز را مشخص کن: صبح/ظهر/عصر/مغرب/عشاء — یا enabled=on/off"
    on_l = (on or "toggle").strip().lower()
    if on_l in {"on", "1", "true", "روشن"}:
        # ensure on
        s = get_azan_settings(user_id) or {}
        if not s.get(key):
            toggle_azan_prayer(user_id, key)
    elif on_l in {"off", "0", "false", "خاموش"}:
        s = get_azan_settings(user_id) or {}
        if s.get(key):
            toggle_azan_prayer(user_id, key)
    else:
        toggle_azan_prayer(user_id, key)
    return "✅ بروزرسانی شد.\n" + _get_azan_settings(user_id)


def _joke_categories() -> str:
    from bot.features.fun.features_fun_fun_tools import get_joke_categories
    labels = get_joke_categories() or {}
    if not labels:
        return "دسته‌بندی جوک در دسترس نیست."
    lines = ["😂 دسته‌های جوک:"]
    for k, v in labels.items():
        lines.append(f"• {k}: {v}")
    lines.append("\nبرای جوک بگو: جوک از دسته X")
    return "\n".join(lines)


async def _download_media(url: str = "", mode: str = "best", user_id: int = 0) -> str:
    url = (url or "").strip()
    if not url:
        return "لینک را بفرست (اینستاگرام، تیک‌تاک، یوتیوب و …)."
    try:
        from bot.services.downloader import download, extract_url
        found = extract_url(url) or url
        result = await download(found, mode=mode or "best", user_id=user_id or None)
        if not result:
            return "دانلود ناموفق بود."
        path = result.get("path") or result.get("file") or ""
        title = result.get("title") or "فایل"
        size = result.get("size") or 0
        method = result.get("method") or ""
        return (
            f"✅ دانلود انجام شد\n"
            f"عنوان: {title}\n"
            f"حجم: {size}\n"
            f"روش: {method}\n"
            f"مسیر موقت: {path}\n"
            "اگر فایل در چت نیامد، همان لینک را مستقیم در ربات بفرست تا به‌صورت فایل ارسال شود."
        )
    except Exception as exc:
        return f"⚠️ دانلود ممکن نشد: {exc}"


async def _generate_image_tool(prompt: str = "") -> str:
    prompt = (prompt or "").strip()
    if not prompt:
        return "توضیح تصویر را بنویس."
    try:
        from bot.services.ai_service import generate_or_edit_image
        img_bytes, mime = await generate_or_edit_image(prompt)
        size = len(img_bytes or b"")
        return (
            f"✅ تصویر ساخته شد ({mime or 'image'}, {size} bytes).\n"
            "برای دریافت فایل تصویری در تلگرام، همین درخواست را با عبارت "
            "«یک تصویر بساز: ...» در چت بفرست تا هندلر رسانه آن را ارسال کند."
        )
    except Exception as exc:
        return f"⚠️ ساخت تصویر ممکن نشد: {exc}"


async def _tts_info(text: str = "", user_id: int = 0) -> str:
    text = (text or "").strip()
    if not text:
        return "متنی برای تبدیل به ویس بفرست."
    try:
        from bot.services.ai_service import text_to_speech
        audio = await text_to_speech(text)
        size = len(audio or b"") if not isinstance(audio, str) else 0
        return (
            f"✅ ویس آماده است (حدود {size} بایت).\n"
            "در چت بگو «ویس بفرست» یا «با ویس جواب بده» تا فایل صوتی ارسال شود."
        )
    except Exception as exc:
        return f"⚠️ ساخت ویس ممکن نشد: {exc}"


def _list_all_capabilities() -> str:
    from bot.services.tool_runtime import get_registered_tool_names, list_registered_tools
    try:
        names = sorted(get_registered_tool_names())
    except Exception:
        names = []
    lines = [
        f"🤖 تعداد ابزارهای متصل به هوش مصنوعی: {len(names)}",
        "همه این قابلیت‌ها از طریق چت قابل فراخوانی هستند:",
        "",
    ]
    for n in names:
        lines.append(f"• {n}")
    lines.append("")
    lines.append("رسانه (تصویر/ویس/ویدیو/دانلود لینک) هم از مسیر پیام تلگرام پشتیبانی می‌شود.")
    return "\n".join(lines)


def register() -> None:
    """Register all bridged tools (idempotent)."""
    global _REGISTERED
    from bot.services.tool_runtime import register_tool, get_registered_tool_names

    existing = set(get_registered_tool_names())

    def add(name, description, parameters, handler, keywords=None, risk="read", network=False):
        if name in existing:
            return
        register_tool(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler,
            keywords=keywords or [],
            risk=risk,
            network=network,
        )
        existing.add(name)

    add(
        "profit_loss",
        "محاسبه سود و ضرر معامله بر اساس قیمت خرید، فروش و تعداد.",
        {"type": "object", "properties": {
            "buy": {"type": "number"},
            "sell": {"type": "number"},
            "qty": {"type": "number"},
        }, "required": ["buy", "sell"]},
        _profit_loss,
        [r"سود\s*و\s*ضرر", r"سود\s*ضرر", r"profit\s*loss"],
    )
    add(
        "analyze_gold",
        "تحلیل زنده طلا / XAU با داده واقعی ربات.",
        {"type": "object", "properties": {"timeframe": {"type": "string"}}},
        _analyze_gold,
        [r"تحلیل\s*طلا", r"طلا\s*چطوره", r"xau", r"gold\s*analysis"],
        network=True,
    )
    add(
        "date_diff",
        "اختلاف دو تاریخ شمسی (به روز/ماه/سال).",
        {"type": "object", "properties": {
            "date1": {"type": "string"}, "date2": {"type": "string"},
            "y1": {"type": "integer"}, "m1": {"type": "integer"}, "d1": {"type": "integer"},
            "y2": {"type": "integer"}, "m2": {"type": "integer"}, "d2": {"type": "integer"},
        }},
        _date_diff,
        [r"اختلاف\s*تاریخ", r"فاصله\s*دو\s*تاریخ"],
    )
    add(
        "age_diff",
        "اختلاف سن دو نفر از روی تاریخ تولد شمسی.",
        {"type": "object", "properties": {
            "birth1": {"type": "string"}, "birth2": {"type": "string"},
            "y1": {"type": "integer"}, "m1": {"type": "integer"}, "d1": {"type": "integer"},
            "y2": {"type": "integer"}, "m2": {"type": "integer"}, "d2": {"type": "integer"},
        }},
        _age_diff,
        [r"اختلاف\s*سن", r"چند\s*سال\s*از\s*هم\s*بزرگتر"],
    )
    add(
        "custom_countdown",
        "شمارش‌معکوس تا یک تاریخ/رویداد دلخواه شمسی.",
        {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
        _custom_countdown,
        [r"شمارش\s*معکوس", r"چند\s*روز\s*مانده", r"countdown"],
    )
    add(
        "list_reminders",
        "لیست یادآوری‌های کاربر.",
        {"type": "object", "properties": {"limit": {"type": "integer"}}},
        _list_reminders,
        [r"لیست\s*یادآوری", r"یادآوری.?ها.?م", r"مدیریت\s*یادآوری"],
        risk="read",
    )
    add(
        "cancel_reminder",
        "لغو یک یادآوری با شناسه.",
        {"type": "object", "properties": {"reminder_id": {"type": "integer"}}, "required": ["reminder_id"]},
        _cancel_reminder,
        [r"لغو\s*یادآوری", r"حذف\s*یادآوری"],
        risk="write",
    )
    add(
        "add_note",
        "ذخیره یادداشت شخصی کاربر.",
        {"type": "object", "properties": {"content": {"type": "string"}}, "required": ["content"]},
        _add_note,
        [r"یادداشت\s*کن", r"نوت\s*ذخیره", r"add\s*note"],
        risk="write",
    )
    add(
        "list_notes",
        "نمایش یادداشت‌های ذخیره‌شده کاربر.",
        {"type": "object", "properties": {"limit": {"type": "integer"}}},
        _list_notes,
        [r"یادداشت.?ها.?م", r"لیست\s*نوت", r"notes"],
    )
    add(
        "delete_note",
        "حذف یادداشت با شناسه.",
        {"type": "object", "properties": {"note_id": {"type": "integer"}}, "required": ["note_id"]},
        _delete_note,
        [r"حذف\s*یادداشت", r"پاک\s*کردن\s*نوت"],
        risk="write",
    )
    add(
        "save_birth_date",
        "ذخیره تاریخ تولد کاربر در پروفایل.",
        {"type": "object", "properties": {"birth_date": {"type": "string"}}, "required": ["birth_date"]},
        _save_birth_date,
        [r"ذخیره\s*تاریخ\s*تولد", r"تولد.?م\s*را?\s*ذخیره"],
        risk="write",
    )
    add(
        "user_stats",
        "آمار استفاده و اطلاعات پروفایل کاربر.",
        {"type": "object", "properties": {}},
        _user_stats,
        [r"آمار\s*من", r"آمار\s*کاربری", r"profile\s*stats"],
    )
    add(
        "set_user_city",
        "تنظیم شهر کاربر برای اذان و هوا.",
        {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
        _set_user_city,
        [r"شهر.?م\s*را?\s*(?:عوض|تنظیم|بگذار)", r"انتخاب\s*شهر", r"set\s*city"],
        risk="write",
    )
    add(
        "set_user_language",
        "تنظیم زبان رابط کاربر (fa/en/ar).",
        {"type": "object", "properties": {"language": {"type": "string"}}, "required": ["language"]},
        _set_user_language,
        [r"زبان.?م\s*را?\s*(?:عوض|کن)", r"set\s*language"],
        risk="write",
    )
    add(
        "get_azan_settings",
        "نمایش وضعیت تنظیمات اذان کاربر.",
        {"type": "object", "properties": {}},
        _get_azan_settings,
        [r"تنظیمات\s*اذان", r"وضعیت\s*اذان"],
    )
    add(
        "set_azan",
        "روشن/خاموش کردن اعلان اذان یا هر نماز (صبح/ظهر/عصر/مغرب/عشاء).",
        {"type": "object", "properties": {
            "enabled": {"type": "string"},
            "prayer": {"type": "string"},
            "on": {"type": "string"},
        }},
        _set_azan,
        [r"اذان\s*را?\s*(?:روشن|خاموش)", r"تنظیم\s*اذان", r"اعلان\s*اذان"],
        risk="write",
    )
    add(
        "joke_categories",
        "لیست دسته‌بندی جوک‌های ربات.",
        {"type": "object", "properties": {}},
        _joke_categories,
        [r"دسته.?بندی\s*جوک", r"انواع\s*جوک"],
    )
    add(
        "download_media",
        "دانلود رسانه از لینک اینستاگرام/تیک‌تاک/یوتیوب و مشابه با موتور دانلودر ربات.",
        {"type": "object", "properties": {
            "url": {"type": "string"},
            "mode": {"type": "string"},
        }, "required": ["url"]},
        _download_media,
        [r"دانلود", r"download", r"اینستا", r"tiktok", r"youtube"],
        network=True,
    )
    add(
        "generate_image",
        "ساخت تصویر از روی توضیح متنی (موتور تصویر ربات).",
        {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]},
        _generate_image_tool,
        [r"تصویر\s*بساز", r"عکس\s*بساز", r"generate\s*image", r"نقاشی\s*کن"],
        network=True,
    )
    add(
        "prepare_tts",
        "آماده‌سازی تبدیل متن به ویس؛ ارسال فایل از مسیر پیام تلگرام انجام می‌شود.",
        {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
        _tts_info,
        [r"ویس\s*بساز", r"متن\s*به\s*صدا", r"tts"],
        network=True,
    )
    add(
        "list_ai_capabilities",
        "فهرست کامل ابزارهای متصل به هوش مصنوعی همین ربات.",
        {"type": "object", "properties": {}},
        _list_all_capabilities,
        [r"چه\s*کارهایی\s*می.?تونی", r"لیست\s*قابلیت", r"امکانات\s*دستیار", r"tools\s*list"],
    )

    _REGISTERED = True
    logger.info("ai_full_bridge: missing capabilities registered")


# Also expose as __ai_tools__ for discovery (handlers bound after register uses functions)
__ai_tools__: list = []  # populated dynamically via register()
