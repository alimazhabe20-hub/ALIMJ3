"""ai_media: voice responsibilities."""
from .ai_media_common import *  # noqa: F401,F403
from . import ai_media_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


async def speech_to_text(
    audio_bytes: bytes,
    *,
    filename: str = "voice.ogg",
    mime: str = "audio/ogg",
) -> str:
    """
    تبدیل ویس/صوت به متن.
    اولویت: Groq Whisper → سپس Gemini.
    """
    if not audio_bytes:
        raise RuntimeError("فایل صوتی خالی است.")

    errors = []

    # ۱) Groq Whisper (سریع و معمولاً رایگان در سهمیه)
    groq_keys = _next_keys("groq")
    if groq_keys:
        import httpx as _httpx

        for key in groq_keys:
            try:
                url = (
                    os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
                    + "/audio/transcriptions"
                )
                model = os.getenv("GROQ_STT_MODEL", "whisper-large-v3-turbo")
                files = {
                    "file": (filename or "audio.ogg", audio_bytes, mime or "audio/ogg"),
                }
                data = {
                    "model": model,
                    "language": os.getenv("STT_LANGUAGE", "fa"),  # فارسی
                    "response_format": "text",
                }
                headers = {"Authorization": f"Bearer {key}"}
                async with _httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.post(
                        url, headers=headers, data=data, files=files
                    )
                if resp.status_code >= 400:
                    if _is_quota_error(resp.status_code, resp.text):
                        _mark_key_cooldown("groq", key, daily=True)
                        errors.append(f"groq STT HTTP {resp.status_code}")
                        continue
                    errors.append(f"groq STT HTTP {resp.status_code}: {resp.text[:200]}")
                    continue
                text = (resp.text or "").strip()
                # گاهی JSON برمی‌گردد
                if text.startswith("{"):
                    try:
                        import json as _json
                        text = (_json.loads(text).get("text") or "").strip()
                    except Exception as _exc:
                        logger.debug("%s: %s", __name__, _exc)
                if text:
                    _advance_rr("groq")
                    return text
                errors.append("groq STT empty")
            except Exception as e:
                errors.append(f"groq STT: {e}")
                continue

    # ۲) Gemini (ورودی audio)
    gemini_keys = _next_keys("gemini")
    if gemini_keys:
        model = os.getenv("GEMINI_STT_MODEL", "gemini-3.1-flash-lite")
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent"
        )
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": mime or "audio/ogg",
                                "data": base64.b64encode(audio_bytes).decode("ascii"),
                            }
                        },
                        {
                            "text": (
                                "این فایل صوتی را دقیقاً به متن پیاده کن. "
                                "فقط متن گفتار را برگردان، بدون توضیح اضافه."
                            )
                        },
                    ],
                }
            ],
            "generationConfig": {"maxOutputTokens": 2048},
            "safetySettings": GEMINI_SAFETY_SETTINGS,
        }
        for key in gemini_keys:
            try:
                status, data = await _post_json(url, params={"key": key}, json=payload)
                if status >= 400:
                    if _is_quota_error(status, data):
                        _mark_key_cooldown("gemini", key, daily=True)
                    errors.append(f"gemini STT HTTP {status}")
                    continue
                parts = data["candidates"][0]["content"]["parts"]
                text = "".join(p.get("text", "") for p in parts).strip()
                if text:
                    _advance_rr("gemini")
                    return text
                errors.append("gemini STT empty")
            except Exception as e:
                errors.append(f"gemini STT: {e}")
                continue

    raise RuntimeError(
        "نتوانستم ویس را به متن تبدیل کنم. کلید Groq یا Gemini لازم است.\n"
        + " | ".join(errors[:5])
    )

async def analyze_voice_emotion(
    audio_bytes: bytes,
    *,
    transcript: str = "",
    filename: str = "voice.ogg",
    mime: str = "audio/ogg",
) -> str:
    """
    تشخیص احساسات و لحن از روی صدا (و در صورت وجود متن پیاده‌شده).
    با Gemini روی خود فایل صوتی کار می‌کند.
    """
    if not audio_bytes:
        raise RuntimeError("فایل صوتی خالی است.")

    keys = _next_keys("gemini")
    if not keys:
        # بدون Gemini: تخمین ضعیف از روی متن
        if transcript:
            return _emotion_from_text_fallback(transcript)
        raise RuntimeError("برای تشخیص احساس از صدا به کلید Gemini نیاز است.")

    if len(audio_bytes) > 4_500_000:
        audio_bytes = audio_bytes[:4_500_000]

    model = os.getenv("GEMINI_EMOTION_MODEL", os.getenv("GEMINI_STT_MODEL", "gemini-3.1-flash-lite"))
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    prompt = (
        "تو یک تحلیل‌گر لحن و احساس صدا هستی. این فایل صوتی را گوش بده "
        "(و اگر متن پیاده‌شده آمد از آن هم کمک بگیر) و به فارسی پاسخ بده.\n\n"
        "ساختار پاسخ دقیقاً این باشد:\n"
        "😊 احساس غالب: ...\n"
        "📊 شدت (۰ تا ۱۰): ...\n"
        "🎙 لحن/انرژی: ...\n"
        "💬 احساسات فرعی: ...\n"
        "📝 توضیح کوتاه: ...\n\n"
        "احساسات ممکن: شادی، غم، عصبانیت، اضطراب، آرامش، هیجان، خستگی، "
        "اعتمادبه‌نفس، تردید، مهربانی، بی‌حوصلگی، ترس، تعجب.\n"
        "اگر صدا واضح نبود صادقانه بگو."
    )
    if transcript:
        prompt += f"\n\nمتن پیاده‌شده از صدا:\n{transcript[:1500]}"

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": mime or "audio/ogg",
                            "data": base64.b64encode(audio_bytes).decode("ascii"),
                        }
                    },
                    {"text": prompt},
                ],
            }
        ],
        "generationConfig": {"maxOutputTokens": 800},
        "safetySettings": GEMINI_SAFETY_SETTINGS,
    }

    errors = []
    for key in keys:
        try:
            status, data = await _post_json(url, params={"key": key}, json=payload)
            if status >= 400:
                if _is_quota_error(status, data):
                    _mark_key_cooldown("gemini", key, daily=True)
                    errors.append(f"HTTP {status}")
                    continue
                raise RuntimeError(f"Gemini emotion HTTP {status}: {str(data)[:400]}")
            parts = data["candidates"][0]["content"]["parts"]
            text = "".join(x.get("text", "") for x in parts).strip()
            if text:
                _advance_rr("gemini")
                return text
            errors.append("empty")
        except Exception as e:
            errors.append(str(e)[:200])
            continue

    if transcript:
        return _emotion_from_text_fallback(transcript)
    raise RuntimeError("تشخیص احساس ناموفق: " + " | ".join(errors[:4]))

def _emotion_from_text_fallback(transcript: str) -> str:
    """تخمین خیلی ساده فقط از روی واژه‌ها (وقتی Gemini نباشد)."""
    t = (transcript or "").lower()
    rules = [
        (["عصبانی", "خفه", "لعنت", "حالم بده از", "کیفم کوک نیست"], "عصبانیت"),
        (["میترسم", "نگران", "استرس", "دلهره"], "اضطراب/نگرانی"),
        (["خوشحالم", "عالی", "محشر", "عاشق", "خنده‌ام"], "شادی"),
        (["غمگین", "گریه", "دلتنگ", "تنها", "سخت"], "غم"),
        (["خسته‌ام", "حالم نیست", "بی‌حال"], "خستگی"),
        (["آروم", "خوبه", "ممنون", "مرسی"], "آرامش"),
    ]
    found = []
    for words, label in rules:
        if any(w in t for w in words):
            found.append(label)
    if not found:
        found = ["خنثی / نامشخص از روی متن"]
    return (
        "😊 احساس غالب (تخمین از متن، نه صدا): "
        + "، ".join(found)
        + "\n📝 برای تشخیص دقیق از لحن صدا، کلید Gemini لازم است."
    )

async def text_to_speech(text: str, *, voice: str | None = None) -> bytes:
    """
    متن → فایل صوتی ogg/mp3 (edge-tts، بدون نیاز به API Key).
    خروجی bytes مناسب ارسال با reply_voice در تلگرام.
    """
    text = (text or "").strip()
    if not text:
        raise RuntimeError("متن خالی است.")
    # تلگرام برای voice محدودیت حدود ۱ دقیقه دارد؛ متن را کمی محدود کن
    if len(text) > 1200:
        text = text[:1200] + " …"

    voice = voice or TTS_VOICE
    try:
        import edge_tts
        import tempfile
        from pathlib import Path as _P

        communicate = edge_tts.Communicate(text, voice)
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tmp = f.name
        await communicate.save(tmp)
        data = _P(tmp).read_bytes()
        try:
            _P(tmp).unlink(missing_ok=True)
        except Exception as _exc:
            logger.debug("%s: %s", __name__, _exc)
        if not data:
            raise RuntimeError("فایل صوتی خالی بود.")
        return data
    except ImportError:
        raise RuntimeError(
            "کتابخانه edge-tts نصب نیست. در requirements.txt بنویس: edge-tts"
        )
    except Exception as e:
        raise RuntimeError(f"ساخت ویس ناموفق: {e}")

def wants_emotion_analysis(text: str) -> bool:
    """آیا کاربر صریحاً تشخیص احساس از صدا خواسته؟"""
    t = (text or "").strip()
    if not t:
        return False
    import re
    patterns = (
        r"تشخیص\s*احساس",
        r"احساس(ات)?\s*(من|صدا|از\s*صدا)?",
        r"لحن(م|م\s*چطور)",
        r"از\s*صدا(م)?\s*(بگو|تحلیل|تشخیص)",
        r"حالم\s*از\s*صدا",
        r"emotion",
        r"تحلیل\s*احساس",
        r"چه\s*احساسی",
    )
    return any(re.search(p, t, re.I) for p in patterns)

def wants_voice_chat_mode(text: str) -> bool:
    """درخواست شروع مکالمه ویسی پایدار (نه فقط یک‌بار)."""
    t = (text or "").strip()
    if not t:
        return False
    import re
    patterns = (
        r"ویس\s*حرف\s*بزن",
        r"با\s*ویس\s*حرف",
        r"حرف\s*بزنیم\s*(با\s*)?ویس",
        r"صحبت\s*(صوتی|ویسی|با\s*صدا)",
        r"چت\s*صوتی",
        r"مکالمه\s*(ی\s*)?(صوتی|ویسی)",
        r"از\s*این\s*به\s*بعد\s*(با\s*)?(ویس|صدا)",
        r"فقط\s*ویس",
        r"voice\s*chat",
        r"let'?s\s*talk\s*(by\s*)?voice",
        r"با\s*صدا\s*حرف",
        r"صدا\s*حرف\s*بزن",
        r"بیا\s*ویس",
        r"ویس\s*باش",
        r"حالت\s*ویس",
        r"حالت\s*صوتی",
    )
    return any(re.search(p, t, re.I) for p in patterns)

def wants_end_voice_chat(text: str) -> bool:
    """پایان حالت مکالمه ویسی."""
    t = (text or "").strip()
    if not t:
        return False
    import re
    patterns = (
        r"قطع\s*ویس",
        r"بدون\s*ویس",
        r"دیگه\s*ویس\s*ن",
        r"متن(ی)?\s*حرف\s*بزن",
        r"حالت\s*متنی",
        r"ویس\s*رو\s*خاموش",
        r"خاموش\s*کردن\s*ویس",
        r"end\s*voice",
        r"stop\s*voice",
        r"فقط\s*متن",
    )
    return any(re.search(p, t, re.I) for p in patterns)

def wants_voice_reply(text: str) -> bool:
    """درخواست صریح ویس برای همین پیام."""
    t = (text or "").strip()
    if not t:
        return False
    import re
    if wants_voice_chat_mode(t):
        return True
    patterns = (
        r"^با\s*ویس\b",
        r"^با\s*صدا\b",
        r"^ویس\s*[:：]",
        r"^صدا\s*[:：]",
        r"ویس\s*بفرست",
        r"صدا\s*بفرست",
        r"بفرست\s*ویس",
        r"بفرست\s*صدا",
        r"فایل\s*صوتی",
        r"صوتی\s*بفرست",
        r"\bبا\s*ویس\s*بگو\b",
        r"\bبا\s*صدا\s*بگو\b",
        r"\bجواب(تو)?\s*(رو\s*)?با\s*ویس\b",
        r"\bجواب(تو)?\s*(رو\s*)?با\s*صدا\b",
        r"\bبرام\s*بخون\b",
        r"\bspeak\b",
        r"\bvoice\s*reply\b",
        r"\btts\b",
        r"send\s*(a\s*)?voice",
    )
    return any(re.search(p, t, re.I) for p in patterns)

def is_voice_only_request(text: str) -> bool:
    """فقط درخواست ویس بدون سؤال دیگر (مثل: ویس بفرست)."""
    t = (text or "").strip()
    if not t:
        return False
    import re
    t2 = re.sub(
        r"^(لطفا|خواهشا|میشه|میتونی|می‌تونی)\s*",
        "",
        t,
        flags=re.I,
    ).strip()
    patterns = (
        r"^ویس\s*بفرست\s*$",
        r"^صدا\s*بفرست\s*$",
        r"^بفرست\s*ویس\s*$",
        r"^بفرست\s*صدا\s*$",
        r"^با\s*ویس\s*$",
        r"^با\s*صدا\s*$",
        r"^بخون\s*$",
        r"^بخوان\s*$",
        r"^voice\s*$",
        r"^tts\s*$",
        r"^فایل\s*صوتی\s*بفرست\s*$",
    )
    return any(re.search(p, t2, re.I) for p in patterns)

def strip_voice_prefix(text: str) -> str:
    import re
    t = (text or "").strip()
    t = re.sub(
        r"^(با\s*ویس|با\s*صدا|ویس|صدا)\s*[:：]?\s*",
        "",
        t,
        flags=re.I,
    )
    t = re.sub(r"\b(با\s*ویس\s*بگو|با\s*صدا\s*بگو)\b", "", t, flags=re.I)
    return t.strip() or text.strip()

def should_auto_voice_reply(
    user_text: str,
    answer: str,
    *,
    input_was_voice: bool = False,
    explicit_voice: bool = False,
    voice_chat_mode: bool = False,
) -> bool:
    """
    ویس فقط وقتی:
      ۱) کاربر صریحاً خواسته (با ویس / بخون / ...)
      ۲) حالت مکالمه ویسی روشن است («ویس حرف بزنیم»)
    ورودی ویس به‌تنهایی کافی نیست — الکی ویس نمی‌فرستد.
    """
    ans = (answer or "").strip()
    if not ans:
        return False

    # فقط درخواست صریح یا حالت مکالمه ویسی
    if explicit_voice or voice_chat_mode:
        return True

    return False
