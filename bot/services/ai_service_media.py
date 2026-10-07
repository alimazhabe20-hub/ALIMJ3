"""ai_service: media responsibilities."""
from .ai_service_common import *  # noqa: F401,F403
from . import ai_service_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


async def _gemini_with_media(
    user_id: int,
    prompt: str,
    model: str,
    media: list[tuple[bytes, str]] | None = None,
) -> str:
    """Gemini multimodal: متن + عکس (و در صورت نیاز چند فایل تصویری)."""
    keys = _next_keys("gemini")
    if not keys:
        raise RuntimeError("هیچ کلید Gemini تنظیم نشده")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    contents = []
    for role, content in _HISTORY[user_id]:
        contents.append(
            {
                "role": "model" if role == "assistant" else "user",
                "parts": [{"text": content}],
            }
        )

    parts = []
    if media:
        for data, mime in media:
            # محدودیت اندازه ~4MB برای inline
            if len(data) > 4_500_000:
                raise RuntimeError("حجم فایل برای تحلیل خیلی بزرگ است (حداکثر حدود ۴ مگابایت).")
            parts.append(
                {
                    "inline_data": {
                        "mime_type": mime or "image/jpeg",
                        "data": base64.b64encode(data).decode("ascii"),
                    }
                }
            )
    parts.append({"text": prompt})
    contents.append({"role": "user", "parts": parts})

    payload = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": contents,
        "generationConfig": {"maxOutputTokens": MAX_OUTPUT},
    }

    errors = []
    for key in keys:
        try:
            status, data = await _post_json(url, params={"key": key}, json=payload)
            if status >= 400:
                if _is_quota_error(status, data):
                    daily = status != 429 or "daily" in str(data).lower() or "quota" in str(data).lower()
                    _mark_key_cooldown("gemini", key, daily=daily)
                    errors.append(f"{_key_id('gemini', key)} HTTP {status}")
                    continue
                raise RuntimeError(f"Gemini HTTP {status}: {str(data)[:900]}")

            try:
                parts_out = data["candidates"][0]["content"]["parts"]
                text = "".join(p.get("text", "") for p in parts_out).strip()
            except Exception:
                raise RuntimeError(f"Gemini unexpected response: {str(data)[:900]}")

            if not text:
                raise RuntimeError("Gemini returned an empty answer")

            _advance_rr("gemini")
            return text
        except RuntimeError as exc:
            if "HTTP" in str(exc) and any(x in str(exc) for x in ("429", "403", "quota")):
                _mark_key_cooldown("gemini", key, daily=True)
                errors.append(str(exc)[:200])
                continue
            errors.append(str(exc)[:200])
            continue

    raise RuntimeError("همه کلیدهای Gemini تمام/خطا: " + " | ".join(errors[:5]))

def _extract_text_from_bytes(data: bytes, filename: str = "", mime: str = "") -> str:
    """استخراج متن از فایل‌های متنی/PDF ساده."""
    name = (filename or "").lower()
    mime = (mime or "").lower()

    # متن ساده
    if (
        mime.startswith("text/")
        or name.endswith((".txt", ".md", ".csv", ".json", ".py", ".js", ".html", ".xml", ".log"))
    ):
        for enc in ("utf-8", "utf-8-sig", "cp1256", "latin-1"):
            try:
                return data.decode(enc)
            except Exception:
                continue
        return data.decode("utf-8", errors="replace")

    # PDF
    if mime == "application/pdf" or name.endswith(".pdf"):
        try:
            from pypdf import PdfReader  # optional
            import io

            reader = PdfReader(io.BytesIO(data))
            pages = []
            for i, page in enumerate(reader.pages[:30]):
                t = page.extract_text() or ""
                if t.strip():
                    pages.append(f"--- صفحه {i+1} ---\n{t}")
            if pages:
                return "\n\n".join(pages)
        except Exception as e:
            logger.warning("pdf extract failed: %s", e)
            return (
                "نتوانستم متن PDF را استخراج کنم. "
                "اگر pypdf نصب باشد یا فایل متنی بفرستی بهتر کار می‌کند."
            )

    # docx
    if name.endswith(".docx") or "wordprocessingml" in mime:
        try:
            import zipfile
            import io
            import re as _re

            with zipfile.ZipFile(io.BytesIO(data)) as z:
                xml = z.read("word/document.xml").decode("utf-8", errors="ignore")
            texts = _re.findall(r"<w:t[^>]*>(.*?)</w:t>", xml)
            return "\n".join(texts) if texts else "متن قابل استخراج از docx نبود."
        except Exception as e:
            logger.warning("docx extract failed: %s", e)
            return "خطا در خواندن فایل Word."

    return ""

async def ask_ai_media(
    user_id: int,
    prompt: str,
    *,
    images: list[tuple[bytes, str]] | None = None,
    file_text: str | None = None,
    filename: str = "",
) -> tuple[str, str]:
    """
    تحلیل عکس و/یا محتوای فایل با AI.
    images: لیست (bytes, mime_type)
    file_text: متن استخراج‌شده از فایل
    """
    prompt = (prompt or "").strip()
    images = images or []

    parts_desc = []
    if images:
        parts_desc.append(f"{len(images)} تصویر")
    if file_text:
        parts_desc.append(f"فایل متنی{(' ' + filename) if filename else ''}")

    if not prompt:
        if images and not file_text:
            prompt = "این تصویر را کامل و دقیق تحلیل کن. محتوا، متن داخل عکس، اشیاء و هر نکته مهم را بگو."
        elif file_text and not images:
            prompt = "محتوای این فایل را کامل بررسی و خلاصهٔ مفید + نکات مهم بده."
        else:
            prompt = "این ورودی را کامل تحلیل کن."

    # متن فایل را به پرامپت بچسبان
    if file_text:
        clipped = file_text[:12000]
        prompt = (
            f"{prompt}\n\n"
            f"[محتوای فایل{(' : ' + filename) if filename else ''}]\n{clipped}"
        )

    if len(prompt) > MAX_INPUT:
        prompt = prompt[:MAX_INPUT]

    options = available_model_options()
    if not options:
        raise RuntimeError("هیچ سرویس AI تنظیم نشده است.")

    original_prompt = prompt if not file_text else (prompt.split("[محتوای فایل")[0].strip() or "تحلیل فایل")

    async with _LOCKS[user_id]:
        selected = get_selected_model(user_id)
        errors: list[str] = []

        # برای تصویر: اولویت با Gemini (بینایی)
        ordered_providers: list[str] = []
        if images:
            ordered_providers.append("gemini")
        if selected:
            p = selected[0]
            if p not in ordered_providers:
                ordered_providers.insert(0, p)
        for p, _l, _m in options:
            if p not in ordered_providers:
                ordered_providers.append(p)

        for provider in ordered_providers:
            models = models_for_provider(provider)
            if not models:
                continue
            for model in models:
                try:
                    if images and provider == "gemini":
                        answer = await _gemini_with_media(
                            user_id, prompt, model, media=images
                        )
                    elif images and provider != "gemini":
                        # مدل‌های بدون بینایی: توضیح بده که تصویر را نمی‌بینند
                        # ولی اگر متن فایل هم هست همان را جواب بدهند
                        if not file_text:
                            raise RuntimeError(
                                f"{provider} از تحلیل تصویر پشتیبانی نمی‌کند؛ Gemini را انتخاب کن."
                            )
                        answer = await _call_provider(provider, user_id, provider_prompt, model)
                    else:
                        answer = await _call_provider(provider, user_id, provider_prompt, model)

                    _save_turn(user_id, original_prompt[:500], answer)
                    if not selected:
                        set_selected_model(user_id, provider, "*")
                    return answer, f"{provider} / {model}"
                except Exception as exc:
                    msg = str(exc).replace("\n", " ")[:400]
                    errors.append(f"{provider}/{model}: {msg}")
                    logger.warning("ask_ai_media failed: %s", msg)
                    await asyncio.sleep(0.05)

    raise RuntimeError(
        "نتوانستم عکس/فایل را تحلیل کنم.\n\n" + "\n".join(errors[:8])
    )

async def generate_or_edit_image(
    prompt: str,
    *,
    source_image: bytes | None = None,
    source_mime: str = "image/jpeg",
) -> tuple[bytes, str]:
    """
    ساخت تصویر از متن، یا ویرایش تصویر با دستور متنی.
    خروجی: (image_bytes, mime_type)
    نیاز به کلید Gemini دارد.
    """
    prompt = (prompt or "").strip()
    if not prompt:
        raise RuntimeError("توضیح تصویر خالی است.")

    keys = _next_keys("gemini")
    if not keys:
        raise RuntimeError("برای ساخت/ویرایش تصویر به کلید Gemini نیاز است.")

    model = IMAGE_GEN_MODEL
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    parts = []
    if source_image:
        if len(source_image) > 4_500_000:
            raise RuntimeError("حجم تصویر برای ویرایش خیلی بزرگ است.")
        parts.append(
            {
                "inline_data": {
                    "mime_type": source_mime or "image/jpeg",
                    "data": base64.b64encode(source_image).decode("ascii"),
                }
            }
        )
        full_prompt = (
            "Edit this image according to the following instruction. "
            "Return the edited image.\n\n" + prompt
        )
    else:
        full_prompt = (
            "Generate a high-quality image for this request. "
            "Return an image.\n\n" + prompt
        )
    parts.append({"text": full_prompt})

    payload = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
        },
    }

    errors = []
    for key in keys:
        try:
            status, data = await _post_json(url, params={"key": key}, json=payload)
            if status >= 400:
                if _is_quota_error(status, data):
                    _mark_key_cooldown("gemini", key, daily=True)
                    errors.append(f"{_key_id('gemini', key)} HTTP {status}")
                    continue
                # fallback مدل قدیمی‌تر
                if "not found" in str(data).lower() or status == 404:
                    alt = os.getenv("GEMINI_IMAGE_MODEL_FALLBACK", "gemini-2.5-flash-image")
                    if model != alt:
                        model = alt
                        url = (
                            f"https://generativelanguage.googleapis.com/v1beta/models/"
                            f"{model}:generateContent"
                        )
                        status, data = await _post_json(
                            url, params={"key": key}, json=payload
                        )
                        if status >= 400:
                            raise RuntimeError(
                                f"Gemini image HTTP {status}: {str(data)[:700]}"
                            )
                    else:
                        raise RuntimeError(
                            f"Gemini image HTTP {status}: {str(data)[:700]}"
                        )
                else:
                    raise RuntimeError(
                        f"Gemini image HTTP {status}: {str(data)[:700]}"
                    )

            candidates = data.get("candidates") or []
            if not candidates:
                raise RuntimeError(f"پاسخ خالی از مدل تصویر: {str(data)[:500]}")

            out_parts = (candidates[0].get("content") or {}).get("parts") or []
            text_bits = []
            image_bytes = None
            mime = "image/png"
            for part in out_parts:
                if "text" in part and part["text"]:
                    text_bits.append(part["text"])
                inline = part.get("inlineData") or part.get("inline_data")
                if inline and inline.get("data"):
                    image_bytes = base64.b64decode(inline["data"])
                    mime = inline.get("mimeType") or inline.get("mime_type") or "image/png"

            if not image_bytes:
                msg = " ".join(text_bits)[:500] or str(data)[:500]
                raise RuntimeError(
                    "مدل تصویری برنگرداند. ممکن است این مدل در کلید شما فعال نباشد یا محدودیت داشته باشد.\n"
                    + msg
                )

            _advance_rr("gemini")
            return image_bytes, mime
        except RuntimeError as exc:
            errors.append(str(exc)[:250])
            continue

    raise RuntimeError(
        "ساخت/ویرایش تصویر ناموفق بود.\n" + " | ".join(errors[:5])
    )

def looks_like_image_request(text: str) -> bool:
    """آیا پیام درخواست ساخت تصویر است؟"""
    t = (text or "").strip()
    if not t:
        return False
    patterns = (
        r"تصویر\s*بساز",
        r"عکس\s*بساز",
        r"عکس\s*تولید",
        r"تصویر\s*تولید",
        r"بکش",
        r"نقاشی\s*کن",
        r"generate\s+(an?\s+)?image",
        r"draw\s+(me\s+)?",
        r"create\s+(an?\s+)?image",
        r"image\s+of",
        r"طراحی\s*کن",
        r"پرامپت\s*تصویر",
    )
    import re
    return any(re.search(p, t, re.I) for p in patterns)

def looks_like_image_edit(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    patterns = (
        r"ویرایش",
        r"تغییر\s*بده",
        r"عوض\s*کن",
        r"اضافه\s*کن",
        r"حذف\s*کن",
        r"edit\s+(this\s+)?image",
        r"change\s+",
        r"remove\s+",
        r"add\s+",
        r"بدل\s*کن",
        r"سبک\s*",
    )
    import re
    return any(re.search(p, t, re.I) for p in patterns)
