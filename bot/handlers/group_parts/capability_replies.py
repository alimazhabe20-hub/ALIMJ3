"""
پاسخ‌های هوشمند برای درخواست‌هایی که محدودیت واقعی تلگرام دارند
یا نیاز به توضیح قابلیت ربات دارند (نه رد خشک AI).

- آنلاین/آفلاین: تلگرام به ربات‌ها وضعیت آنلاین نمی‌دهد
- ارسال پیام خصوصی به کاربر دیگر: فقط اگر خودش قبلاً ربات را استارت کرده باشد
- ارسال پیام داخل همین گروه: ممکن است
- نقش‌آفرینی/اسم مستعار فان: مجاز و دوستانه
- «وقتی فلان نفر پیام داد بگو X»: ذخیره پیام معلق و تحویل هنگام پیام بعدی او
"""
from __future__ import annotations

import re
import time
from typing import Optional, Tuple, Dict, Any

from bot.logger import logger

# chat_id -> list of pending {target_norm, target_display, text, from_user_id, from_name, created}
_PENDING: Dict[int, list] = {}
_PENDING_TTL = 6 * 3600  # 6 hours
_PENDING_MAX_PER_CHAT = 12


def _norm_name(s: str) -> str:
    s = (s or "").strip().lower()
    s = s.replace("\u200c", " ").replace("@", "")
    s = re.sub(r"\s+", " ", s)
    return s


def _clean_pending() -> None:
    now = time.time()
    for cid in list(_PENDING.keys()):
        items = [p for p in _PENDING.get(cid, []) if now - p.get("created", 0) < _PENDING_TTL]
        if items:
            _PENDING[cid] = items[-_PENDING_MAX_PER_CHAT:]
        else:
            _PENDING.pop(cid, None)


# ── الگوهای تشخیص ──────────────────────────────────────────────────────────

# «هر وقت X آنلاین شد بهش بگو ...»
ONLINE_NOTIFY_RE = re.compile(
    r"(?:"
    r"(?:هر\s*وقت|وقتی|هرزمان|هر\s*زمان|به\s*محض\s*اینکه|به\s*مجرد)\s+"
    r".{0,40}?"
    r"(?:آنلاین|آن\s*لاین|online|اونلاین|وارد\s*(?:شد|بشه|بشود)|فعال\s*شد)"
    r"|"
    r"(?:وضعیت|پیگیری|چک)\s*(?:آنلاین|آن\s*لاین|online)"
    r"|"
    r"(?:بگو|خبر\s*بده|اطلاع\s*بده).{0,30}(?:آنلاین|آن\s*لاین|online)"
    r")",
    re.I,
)

# «به X بگو / پیام بفرست / صدا بزن» (ارسال به کاربر دیگر)
SEND_TO_USER_RE = re.compile(
    r"(?:"
    r"(?:به|برای)\s+([^\s،,]+(?:\s+[^\s،,]{1,20}){0,2})\s+"
    r"(?:بگو|بفرست|پیام\s*بده|پیام\s*بفرست|بگو\s*که|بگو\s*بگه|صدا\s*بزن|خبر\s*بده)"
    r"|"
    r"(?:پیام|پیغام)\s*(?:بفرست|بده|ارسال\s*کن)\s*(?:به|برای)\s+([^\s،,]+)"
    r"|"
    r"(?:صدا\s*بزن|صداش\s*کن|منشن\s*کن)\s+([^\s،,]+)"
    r")",
    re.I,
)

# «وقتی X توی گروه پیام داد / اومد بگو ...»
WHEN_SPEAKS_RE = re.compile(
    r"(?:"
    r"(?:هر\s*وقت|وقتی|هرزمان)\s+"
    r"([^\s،,]{2,30}(?:\s+[^\s،,]{1,20}){0,2})\s+"
    r"(?:پیام\s*(?:داد|بده|فرستاد|فرستاد)|اومد|آمد|حرف\s*زد|صحبت\s*کرد|نوشت)"
    r".{0,10}?"
    r"(?:بهش\s*)?(?:بگو|بفرست|بگو\s*که)"
    r"|"
    r"(?:به|برای)\s+([^\s،,]{2,30})\s+"
    r"(?:بگو|بفرست).{0,40}?"
    r"(?:وقتی|هر\s*وقت).{0,20}?(?:پیام|گروه|اومد)"
    r")",
    re.I,
)

# درخواست فان / اسم مستعار / نقش‌آفرینی
FUN_ROLEPLAY_RE = re.compile(
    r"(?:"
    r"(?:صداش\s*کن|صدا\s*بزن|بهش\s*بگو|اسمش\s*رو\s*بذار|اسم\s*مستعار|لقب)"
    r".{0,40}?"
    r"(?:جاستین|بیبر|پاف|ددی|justin|bieber|puff|daddy|هیولا|غول|شاه|ملکه|آقا|خانم)"
    r"|"
    r"(?:از\s*این\s*به\s*بعد|ازین\s*به\s*بعد).{0,30}?(?:صدا|بگو|اسم)"
    r")",
    re.I,
)

# درخواست اطلاعات شخصی کاربر دیگر
PERSONAL_INFO_RE = re.compile(
    r"(?:"
    r"(?:اسم\s*(?:واقعی|حقیقی|کامل)|نام\s*(?:واقعی|حقیقی)|اطلاعات\s*شخصی|شماره|آیدی\s*عددی|یوزرنیم\s*واقعی)"
    r".{0,25}?"
    r"(?:کاربر|این\s*کاربر|اون|او|این)"
    r"|"
    r"(?:کاربر|این)\s+\S+.{0,15}?(?:اسم\s*(?:واقعی|حقیقی)|کیه|چه\s*کسیه|اطلاعات)"
    r")",
    re.I,
)


def detect_capability_intent(text: str) -> Tuple[Optional[str], Dict[str, Any]]:
    """
    Returns (intent_name, meta) or (None, {}).
    intents: online_notify, send_to_user, when_speaks, fun_roleplay, personal_info
    """
    t = (text or "").strip()
    if not t:
        return None, {}

    if ONLINE_NOTIFY_RE.search(t):
        # استخراج نام هدف اگر ممکن باشد
        m = re.search(
            r"(?:هر\s*وقت|وقتی)\s+([^\s،,]{2,25}(?:\s+[^\s،,]{1,15}){0,2})\s+(?:آنلاین|آن\s*لاین|online)",
            t,
            re.I,
        )
        target = m.group(1).strip() if m else ""
        return "online_notify", {"target": target, "raw": t}

    if WHEN_SPEAKS_RE.search(t):
        m = WHEN_SPEAKS_RE.search(t)
        target = ""
        if m:
            target = (m.group(1) or m.group(2) or "").strip()
        # متنی که باید گفته شود
        msg_m = re.search(r"(?:بگو|بفرست|بگو\s*که)\s*[:：]?\s*(.+)$", t, re.I | re.S)
        payload = (msg_m.group(1).strip() if msg_m else "")[:500]
        return "when_speaks", {"target": target, "payload": payload, "raw": t}

    if FUN_ROLEPLAY_RE.search(t):
        return "fun_roleplay", {"raw": t}

    if PERSONAL_INFO_RE.search(t):
        return "personal_info", {"raw": t}

    if SEND_TO_USER_RE.search(t):
        m = SEND_TO_USER_RE.search(t)
        target = ""
        if m:
            target = (m.group(1) or m.group(2) or m.group(3) or "").strip()
        msg_m = re.search(r"(?:بگو|بفرست|بگو\s*که)\s*[:：]?\s*(.+)$", t, re.I | re.S)
        payload = (msg_m.group(1).strip() if msg_m else "")[:500]
        return "send_to_user", {"target": target, "payload": payload, "raw": t}

    return None, {}


def reply_online_notify(target: str = "") -> str:
    who = f"«{target}»" if target else "کسی"
    return (
        f"متأسفم، تلگرام به ربات‌ها وضعیت آنلاین/آفلاین کاربران را نمی‌دهد؛ "
        f"بنابراین نمی‌تونم بفهمم {who} کی آنلاین می‌شه.\n\n"
        "✅ اما می‌تونم این کار رو برات انجام بدم:\n"
        "• وقتی همون نفر توی <b>همین گروه</b> پیام داد، پیامت رو بهش برسونم.\n"
        "مثال: «ربات هر وقت علیرضا پیام داد بگو الس اوکی؟»"
    )


def reply_send_to_user(target: str = "", payload: str = "", *, in_group: bool = True) -> str:
    who = target or "اون کاربر"
    if in_group:
        return (
            f"من نمی‌تونم پیام خصوصی به {who} بفرستم مگر اینکه خودش قبلاً ربات رو در پیوی استارت کرده باشه.\n\n"
            "✅ توی <b>همین گروه</b> می‌تونم:\n"
            f"• پیامت رو اینجا بنویسم و اگر ممکن باشه منشن کنم.\n"
            "• یا وقتی اون نفر پیام داد، پیامت رو براش تحویل بدم.\n\n"
            "اگر می‌خوای الان توی گروه گفته بشه، بگو «همین الان توی گروه بگو: ...»\n"
            "اگر می‌خوای وقتی پیام داد برسونم، بگو «هر وقت [اسم] پیام داد بگو ...»"
        )
    return (
        f"برای ارسال پیام خصوصی به {who}، اون کاربر باید قبلاً ربات را در چت خصوصی استارت کرده باشد. "
        "در غیر این صورت تلگرام اجازه نمی‌دهد."
    )


def reply_personal_info() -> str:
    return (
        "من به اطلاعات شخصی کاربران (اسم واقعی، شماره، و غیره) دسترسی ندارم و "
        "نمی‌تونم چیزی از خودم در مورد هویت افراد بسازم.\n\n"
        "فقط چیزی که خود کاربر در گروه نوشته یا نمایش داده را می‌بینم."
    )


def reply_fun_roleplay_hint() -> str:
    """راهنمای کوتاه؛ پاسخ اصلی را AI با لحن فان می‌دهد."""
    return ""  # خالی = بگذار AI جواب دهد، فقط پرامپت تقویت می‌شود


def add_pending_message(
    chat_id: int,
    *,
    target: str,
    payload: str,
    from_user_id: int,
    from_name: str,
) -> str:
    """ذخیره پیام معلق برای وقتی کاربر هدف در گروه پیام بدهد."""
    _clean_pending()
    target_n = _norm_name(target)
    if not target_n or not payload:
        return (
            "برای ثبت پیام معلق، اسم طرف و متن پیام را مشخص کن.\n"
            "مثال: «ربات هر وقت علیرضا پیام داد بگو الس اوکی؟»"
        )
    lst = _PENDING.setdefault(chat_id, [])
    lst.append(
        {
            "target_norm": target_n,
            "target_display": target.strip(),
            "text": payload.strip()[:500],
            "from_user_id": from_user_id,
            "from_name": (from_name or "")[:40],
            "created": time.time(),
        }
    )
    if len(lst) > _PENDING_MAX_PER_CHAT:
        _PENDING[chat_id] = lst[-_PENDING_MAX_PER_CHAT:]
    return (
        f"✅ ثبت شد.\n"
        f"وقتی <b>{target.strip()}</b> توی این گروه پیام بده، می‌گم:\n"
        f"«{payload.strip()[:200]}»\n\n"
        f"<i>(حداکثر ۶ ساعت معتبر — از طرف {from_name or 'شما'})</i>"
    )


def pop_pending_for_user(chat_id: int, user) -> list:
    """اگر کاربری که الان پیام داده هدف پیام‌های معلق باشد، آن‌ها را برگردان و حذف کن."""
    _clean_pending()
    items = _PENDING.get(chat_id) or []
    if not items or not user:
        return []

    names = set()
    for attr in ("first_name", "last_name", "username", "full_name"):
        v = getattr(user, attr, None) or ""
        if v:
            names.add(_norm_name(v))
    # ترکیب نام
    fn = (getattr(user, "first_name", None) or "").strip()
    ln = (getattr(user, "last_name", None) or "").strip()
    if fn and ln:
        names.add(_norm_name(f"{fn} {ln}"))

    matched = []
    remain = []
    for p in items:
        tn = p.get("target_norm") or ""
        hit = False
        for n in names:
            if not n:
                continue
            if tn == n or tn in n or n in tn:
                hit = True
                break
            # تطبیق جزئی برای اسم‌های کوتاه
            if len(tn) >= 3 and (tn in n or n.startswith(tn) or tn.startswith(n)):
                hit = True
                break
        if hit:
            matched.append(p)
        else:
            remain.append(p)

    if remain:
        _PENDING[chat_id] = remain
    else:
        _PENDING.pop(chat_id, None)
    return matched


def format_pending_delivery(pending_list: list) -> str:
    if not pending_list:
        return ""
    lines = []
    for p in pending_list:
        who = p.get("from_name") or "یکی"
        lines.append(f"📩 پیام از <b>{who}</b>:\n{p.get('text', '')}")
    return "\n\n".join(lines)


def build_capability_ai_hint(intent: str, meta: dict) -> str:
    """پسوند پرامپت برای AI تا جواب دقیق و مفید بدهد."""
    if intent == "online_notify":
        return (
            "\n\n[واقعیت فنی] تلگرام به ربات وضعیت آنلاین/آفلاین نمی‌دهد. "
            "این را شفاف بگو و پیشنهاد جایگزین بده: ثبت پیام برای وقتی همان نفر در گروه پیام داد. "
            "هرگز نگوی که می‌توانی آنلاین بودن را چک کنی."
        )
    if intent == "send_to_user":
        return (
            "\n\n[واقعیت فنی] ربات می‌تواند داخل همین گروه پیام بفرستد، "
            "اما پیام خصوصی به کاربر دیگر فقط اگر خودش ربات را استارت کرده باشد ممکن است. "
            "پیشنهاد بده: پیام را الان در گروه بنویسی یا برای وقتی او پیام داد نگه داری. "
            "خشک و ربات‌مانند رد نکن؛ راهنمایی کن."
        )
    if intent == "fun_roleplay":
        return (
            "\n\n[لحن] این درخواست فان/نقش‌آفرینی گروهی است. "
            "با شوخی و مهربانی جواب بده، اسم مستعار را بپذیر یا بازی کن. "
            "رد خشک نکن مگر محتوای خطرناک یا مربوط به افراد زیر ۱۸ باشد."
        )
    if intent == "personal_info":
        return (
            "\n\n[حریم خصوصی] اطلاعات شخصی کاربران را نداری و نباید حدس بزنی. "
            "مودبانه بگو دسترسی نداری. اگر کاربر خودش چیزی گفته، فقط همان را تکرار نکن مگر لازم باشد."
        )
    return ""
