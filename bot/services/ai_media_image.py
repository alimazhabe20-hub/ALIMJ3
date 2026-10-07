"""ai_media: image responsibilities."""
from .ai_media_common import *  # noqa: F401,F403
from . import ai_media_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


async def _get_image_bytes(url: str, *, headers=None) -> tuple[int, bytes, str]:
    """GET image endpoint and return status, bytes, content-type."""
    client = _get_http()
    response = await client.get(url, headers=headers, follow_redirects=True)
    return response.status_code, response.content, response.headers.get("content-type", "")

async def _generate_image_pollinations(prompt: str) -> tuple[bytes, str]:
    """Pollinations anonymous/free fallback. No key is required for the fallback path."""
    model = os.getenv("POLLINATIONS_IMAGE_MODEL", "flux").strip() or "flux"
    width = int(os.getenv("POLLINATIONS_IMAGE_WIDTH", "1024"))
    height = int(os.getenv("POLLINATIONS_IMAGE_HEIGHT", "1024"))
    encoded = quote(prompt, safe="")
    urls = [
        f"https://gen.pollinations.ai/image/{encoded}?model={quote(model)}&width={width}&height={height}",
        f"https://image.pollinations.ai/prompt/{encoded}?width={width}&height={height}",
    ]
    errors = []
    for url in urls:
        try:
            status, content, mime = await _get_image_bytes(url)
            if status < 400 and content and (content.startswith(b"\\x89PNG") or content.startswith(b"\\xff\\xd8") or "image" in mime.lower()):
                return content, mime or "image/png"
            errors.append(f"HTTP {status}")
        except Exception as exc:
            errors.append(str(exc)[:200])
    raise RuntimeError("Pollinations در دسترس نبود: " + " | ".join(errors[:3]))

def _find_local_image_model() -> Optional[str]:
    """فقط مدل‌هایی را برمی‌گرداند که واقعاً روی سیستم موجودند؛ دانلود خودکار انجام نمی‌دهد."""
    candidates = []
    configured = os.getenv("LOCAL_IMAGE_MODEL_PATH", "").strip()
    if configured:
        candidates.append(configured)
    for raw in os.getenv("LOCAL_IMAGE_MODEL_PATHS", "./models/image,./models/sd15,./models/sdxl,/models/image").split(","):
        raw = raw.strip()
        if raw:
            candidates.append(raw)
    for item in candidates:
        path = Path(item).expanduser()
        if path.exists() and path.is_dir():
            # diffusers models normally have model_index.json; allow common single-file dirs too.
            if (path / "model_index.json").exists() or any(path.glob("*.safetensors")):
                return str(path)
    return None

async def _detect_local_backend() -> tuple[str, str] | None:
    """هوشمندانه backend محلی موجود را پیدا می‌کند؛ هیچ چیزی دانلود نمی‌شود."""
    global _LOCAL_BACKEND_CACHE
    if _LOCAL_BACKEND_CACHE is not None:
        return _LOCAL_BACKEND_CACHE

    client = _get_http()
    candidates = []
    configured = os.getenv("LOCAL_IMAGE_API_URL", "").strip().rstrip("/")
    if configured:
        candidates.append(("a1111", configured))
    candidates.extend([
        ("a1111", "http://127.0.0.1:7860"),
        ("comfyui", "http://127.0.0.1:8188"),
    ])

    for backend, base in candidates:
        try:
            if backend == "a1111":
                r = await client.get(f"{base}/sdapi/v1/sd-models", timeout=3)
                if r.status_code < 400:
                    _LOCAL_BACKEND_CACHE = (backend, base)
                    return _LOCAL_BACKEND_CACHE
            else:
                r = await client.get(f"{base}/system_stats", timeout=3)
                if r.status_code < 400:
                    _LOCAL_BACKEND_CACHE = (backend, base)
                    return _LOCAL_BACKEND_CACHE
        except Exception:
            continue

    model_path = _find_local_image_model()
    if model_path:
        _LOCAL_BACKEND_CACHE = ("diffusers", model_path)
        return _LOCAL_BACKEND_CACHE
    return None

async def _generate_image_a1111(prompt: str, base_url: str) -> tuple[bytes, str]:
    """تولید تصویر از Stable Diffusion WebUI/Forge API روی همان سرور."""
    client = _get_http()
    payload = {
        "prompt": prompt,
        "steps": int(os.getenv("LOCAL_IMAGE_STEPS", "20")),
        "width": int(os.getenv("LOCAL_IMAGE_WIDTH", "512")),
        "height": int(os.getenv("LOCAL_IMAGE_HEIGHT", "512")),
        "batch_size": 1,
        "n_iter": 1,
    }
    response = await client.post(
        f"{base_url}/sdapi/v1/txt2img",
        json=payload,
        timeout=max(TIMEOUT, 120),
    )
    if response.status_code >= 400:
        raise RuntimeError(f"A1111 HTTP {response.status_code}: {response.text[:300]}")
    data = response.json()
    images = data.get("images") or []
    if not images:
        raise RuntimeError("A1111 تصویری برنگرداند")
    return base64.b64decode(images[0]), "image/png"

async def _generate_image_local(prompt: str) -> tuple[bytes, str]:
    """Local fallback with automatic backend detection (A1111/Forge → Diffusers)."""
    global _LOCAL_PIPELINE, _LOCAL_PIPELINE_MODEL

    backend = await _detect_local_backend()
    if not backend:
        raise RuntimeError("هیچ موتور تصویر محلی روی سرور پیدا نشد")

    backend_name, backend_value = backend
    if backend_name == "a1111":
        return await _generate_image_a1111(prompt, backend_value)

    model_path = backend_value if backend_name == "diffusers" else _find_local_image_model()
    if not model_path:
        raise RuntimeError("مدل Diffusers محلی پیدا نشد")

    try:
        import io
        import torch
        from diffusers import AutoPipelineForText2Image
    except Exception as exc:
        raise RuntimeError(f"وابستگی‌های local image نصب نیستند: {exc}")

    if _LOCAL_PIPELINE is None or _LOCAL_PIPELINE_MODEL != model_path:
        def _load():
            pipe = AutoPipelineForText2Image.from_pretrained(
                model_path,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                local_files_only=True,
            )
            if torch.cuda.is_available():
                pipe = pipe.to("cuda")
            return pipe
        _LOCAL_PIPELINE = await asyncio.to_thread(_load)
        _LOCAL_PIPELINE_MODEL = model_path

    def _run():
        image = _LOCAL_PIPELINE(prompt, num_inference_steps=int(os.getenv("LOCAL_IMAGE_STEPS", "20"))).images[0]
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        return buf.getvalue()

    return await asyncio.to_thread(_run), "image/png"

async def generate_or_edit_image(
    prompt: str,
    *,
    source_image: bytes | None = None,
    source_mime: str = "image/jpeg",
) -> tuple[bytes, str]:
    """ساخت/ویرایش تصویر با انتخاب خودکار اولین سرویس در دسترس.

    ترتیب پیش‌فرض: Gemini → Pollinations → Local.
    سرویس‌هایی که کلید/مدل لازم را ندارند خودکار رد می‌شوند. برای ویرایش عکس،
    سرویس‌هایی که فقط text-to-image هستند برای ویرایش عکس رد می‌شوند.
    """
    prompt = (prompt or "").strip()
    if not prompt:
        raise RuntimeError("توضیح تصویر خالی است.")

    errors: List[str] = []

    # 1) Gemini: اگر کلید موجود باشد امتحان می‌شود؛ quota failure جلوی fallback را نمی‌گیرد.
    gemini_keys = _next_keys("gemini")
    if gemini_keys:
        models: List[str] = []
        for candidate in (IMAGE_GEN_MODEL, *IMAGE_GEN_MODEL_FALLBACKS):
            candidate = (candidate or "").strip()
            if candidate and candidate not in models:
                models.append(candidate)
        parts = []
        if source_image:
            if len(source_image) > 4_500_000:
                raise RuntimeError("حجم تصویر برای ویرایش خیلی بزرگ است.")
            parts.append({"inline_data": {"mime_type": source_mime or "image/jpeg", "data": base64.b64encode(source_image).decode("ascii")}})
            full_prompt = "Edit this image according to the following instruction. Return the edited image.\n\n" + prompt
        else:
            full_prompt = "Generate a high-quality image for this request. Return an image.\n\n" + prompt
        parts.append({"text": full_prompt})
        payload = {"contents": [{"role": "user", "parts": parts}], "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]}, "safetySettings": GEMINI_SAFETY_SETTINGS}

        for key in gemini_keys:
            for model in models:
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                    status, data = await _post_json(url, params={"key": key}, json=payload)
                    if status >= 400:
                        err = data.get("error", {}) if isinstance(data, dict) else {}
                        detail = str(err.get("message") or err.get("status") or data).replace("\n", " ")[:450]
                        errors.append(f"gemini/{model} HTTP {status}: {detail}")
                        if _is_quota_error(status, data):
                            _mark_key_cooldown("gemini", key, daily=(status == 403))
                        continue
                    for part in ((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []:
                        inline = part.get("inlineData") or part.get("inline_data")
                        if inline and inline.get("data"):
                            return base64.b64decode(inline["data"]), inline.get("mimeType") or inline.get("mime_type") or "image/png"
                    errors.append(f"gemini/{model}: تصویر برنگشت")
                except Exception as exc:
                    errors.append(f"gemini/{model}: {str(exc)[:250]}")
    else:
        errors.append("gemini: کلید موجود نیست")

    # 2) Pollinations: بدون کلید امتحان می‌شود؛ برای text-to-image.
    if not source_image:
        try:
            return await _generate_image_pollinations(prompt)
        except Exception as exc:
            errors.append(f"pollinations: {str(exc)[:350]}")
    else:
        errors.append("pollinations: برای ویرایش عکس رد شد")

    # 3) Local: فقط اگر مدل از قبل روی دیسک موجود باشد؛ هیچ دانلود خودکاری انجام نمی‌شود.
    try:
        return await _generate_image_local(prompt)
    except Exception as exc:
        errors.append(f"local: {str(exc)[:350]}")

    raise RuntimeError(
        "هیچ سرویس تصویر در دسترس نبود. سیستم همه گزینه‌های موجود را خودکار بررسی کرد.\n"
        + " | ".join(errors[:10])
    )

def extract_image_prompt(text: str) -> str:
    """دستور ساخت تصویر را از فرمان کاربر جدا می‌کند."""
    t = (text or "").strip()
    if not t:
        return ""
    import re
    patterns = (
        r"^/image(?:@\w+)?\s*[:：-]?\s*",
        r"^(?:تصویر|عکس)\s*(?:بساز|تولید کن|تولیدش کن|درست کن)\s*[:：-]?\s*",
        r"^(?:یک|یه)\s+(?:تصویر|عکس)\s+(?:بساز|درست کن)\s*[:：-]?\s*",
        r"^(?:generate|create)\s+(?:an?\s+)?image\s*[:：-]?\s*",
        r"^draw(?:\s+me)?\s*[:：-]?\s*",
    )
    for pattern in patterns:
        cleaned = re.sub(pattern, "", t, count=1, flags=re.I).strip()
        if cleaned != t:
            return cleaned[:5000]
    return t[:5000]

def looks_like_image_request(text: str) -> bool:
    """آیا پیام درخواست ساخت تصویر است؟"""
    t = (text or "").strip()
    if not t:
        return False
    # درخواست‌های صریح ساخت تصویر
    patterns = (
        r"تصویر\s*(?:بساز|تولید(?:\s*کن|ش\s*کن)?|درست\s*کن|ایجاد\s*کن)",
        r"عکس\s*(?:بساز|تولید(?:\s*کن|ش\s*کن)?|درست\s*کن|ایجاد\s*کن)",
        r"(?:نقاشی|طرح|پوستر|پرتره|لوگو|والپیپر|تصویرسازی)\s*(?:بساز|درست\s*کن|ایجاد\s*کن|طراحی\s*کن)",
        r"بکش",
        r"نقاشی\s*کن",
        r"طراحی\s*کن",
        r"پرامپت\s*تصویر",
        r"generate\s+(?:an?\s+)?image",
        r"draw(?:\s+me)?\s+",
        r"create\s+(?:an?\s+)?image",
        r"image\s+of",
    )
    import re
    if any(re.search(p, t, re.I) for p in patterns):
        return True

    # حالت محاوره‌ای فارسی مثل: «یک پارک در حال باران بساز»
    # فقط وقتی فعال می‌شود که فعل ساخت با یک موضوع بصری همراه باشد تا
    # درخواست‌هایی مثل «یک برنامه بساز» اشتباهاً تصویر محسوب نشوند.
    visual_terms = (
        r"عکس|تصویر|پارک|منظره|طبیعت|آسمان|دریا|کوه|جنگل|خیابان|شهر|خانه|"
        r"ماشین|موتور|شخص|مرد|زن|بچه|کاراکتر|شخصیت|حیوان|گربه|سگ|"
        r"باران|برف|غروب|طلوع|ماه|خورشید|گل|درخت|دشت|ساحل|لوگو|پوستر|"
        r"پرتره|نقاشی|طرح|والپیپر|فانتزی|سینمایی|واقع‌گرایانه|انیمه"
    )
    creation_verbs = r"بساز|درست\s*کن|ایجاد\s*کن|تولید\s*کن|طراحی\s*کن"
    if re.search(rf"(?:^|\s)(?:یک|یه|یکى)?\s*.+\s+(?:{creation_verbs})\s*$", t, re.I):
        return bool(re.search(visual_terms, t, re.I))

    return False

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
