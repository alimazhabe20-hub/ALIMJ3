"""ai_media: creative responsibilities."""
from .ai_media_common import *  # noqa: F401,F403
from . import ai_media_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


async def generate_music(prompt: str) -> bytes:
    """
    ساخت کلیپ صوتی.
    اولویت: مدل‌های Lyria / پاسخ AUDIO در Gemini.
    اگر API موسیقی ندهد، خطای واضح برمی‌گرداند.
    """
    prompt = (prompt or "").strip()
    if not prompt:
        raise RuntimeError("توضیح موسیقی خالی است.")
    keys = _next_keys("gemini")
    if not keys:
        raise RuntimeError("برای ساخت موسیقی به کلید Gemini نیاز است.")

    models = [
        os.getenv("GEMINI_MUSIC_MODEL", "").strip(),
        "lyria-3-clip-preview",
        "lyria-3-pro-preview",
    ]
    models = [m for m in models if m]
    # حذف تکراری با حفظ ترتیب
    seen = set()
    models = [m for m in models if not (m in seen or seen.add(m))]

    errors = []
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        payloads = [
        {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        },
    ]
        for key in keys:
            for payload in payloads:
                try:
                    status, data = await _post_json(url, params={"key": key}, json=payload)
                    if status >= 400:
                        errors.append(f"{model} HTTP {status}")
                        if _is_quota_error(status, data):
                            _mark_key_cooldown("gemini", key, daily=True)
                        continue
                    parts = (data.get("candidates") or [{}])[0].get("content", {}).get("parts") or []
                    for part in parts:
                        inline = part.get("inlineData") or part.get("inline_data")
                        if inline and inline.get("data"):
                            raw = base64.b64decode(inline["data"])
                            if raw:
                                _advance_rr("gemini")
                                return raw
                    errors.append(f"{model}: no audio part")
                except Exception as e:
                    errors.append(str(e)[:120])
    raise RuntimeError(
        "ساخت موسیقی روی این کلید/مدل در دسترس نبود. "
        "مدل Lyria باید روی پروژه Google AI Studio فعال باشد.\n"
        + " | ".join(errors[:5])
    )

async def analyze_video(
    video_bytes: bytes,
    prompt: str = "",
    *,
    mime: str = "video/mp4",
) -> str:
    """تحلیل ویدیو کوتاه با Gemini."""
    keys = _next_keys("gemini")
    if not keys:
        raise RuntimeError("برای تحلیل ویدیو به Gemini نیاز است.")
    if len(video_bytes) > 15_000_000:
        raise RuntimeError("ویدیو خیلی بزرگ است (حد حدود ۱۵ مگ).")

    model = os.getenv("GEMINI_VIDEO_MODEL", "gemini-3.1-flash-lite")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    text = (prompt or "").strip() or (
        "این ویدیو کوتاه را خلاصه و تحلیل کن: موضوع، افراد/اشیاء مهم، "
        "متن یا گفتار شنیده‌شده، و نکات کلیدی."
    )
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": mime or "video/mp4",
                            "data": base64.b64encode(video_bytes).decode("ascii"),
                        }
                    },
                    {"text": text},
                ],
            }
        ],
        "generationConfig": {"maxOutputTokens": MAX_OUTPUT},
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
            parts = data["candidates"][0]["content"]["parts"]
            out = "".join(x.get("text", "") for x in parts).strip()
            if out:
                _advance_rr("gemini")
                return out
        except Exception as e:
            errors.append(str(e)[:150])
    raise RuntimeError("تحلیل ویدیو ناموفق: " + " | ".join(errors[:4]))

async def translate_voice(
    audio_bytes: bytes,
    *,
    target_lang: str = "en",
    filename: str = "voice.ogg",
    mime: str = "audio/ogg",
) -> tuple[str, str, bytes]:
    """ویس → متن → ترجمه → ویس مقصد. خروجی: (متن اصلی, ترجمه, audio)."""
    src_text = await speech_to_text(audio_bytes, filename=filename, mime=mime)
    target_lang = (target_lang or "en").lower()
    lang_name = {
        "en": "English",
        "fa": "Persian",
        "ar": "Arabic",
        "tr": "Turkish",
        "de": "German",
        "fr": "French",
    }.get(target_lang, target_lang)

    prompt = (
        "Translate the following text to "
        + lang_name
        + ". Return only the translation.\n\n"
        + src_text
    )
    translated = None
    options = available_model_options()
    for provider, _label, model in options:
        try:
            translated = await _call_provider(provider, 0, prompt, model)
            if translated:
                break
        except Exception:
            continue
    if not translated:
        raise RuntimeError("ترجمه ناموفق بود.")

    voice = TTS_VOICE
    if target_lang.startswith("en"):
        voice = "en-US-JennyNeural"
    elif target_lang.startswith("ar"):
        voice = "ar-SA-ZariyahNeural"
    elif target_lang.startswith("de"):
        voice = "de-DE-KatjaNeural"
    elif target_lang.startswith("fr"):
        voice = "fr-FR-DeniseNeural"
    elif target_lang.startswith("tr"):
        voice = "tr-TR-EmelNeural"
    elif target_lang.startswith("fa"):
        voice = TTS_VOICE

    audio_out = await text_to_speech(translated, voice=voice)
    return src_text, translated, audio_out
