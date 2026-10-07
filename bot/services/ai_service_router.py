"""ai_service: router responsibilities."""
from .ai_service_common import *  # noqa: F401,F403
from . import ai_service_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


async def ask_ai(user_id: int, prompt: str) -> tuple[str, str]:
    prompt = (prompt or "").strip()
    if not prompt:
        raise RuntimeError("پیام خالی است")
    if len(prompt) > MAX_INPUT:
        prompt = prompt[:MAX_INPUT]

    options = available_model_options()
    if not options:
        raise RuntimeError(
            "هیچ سرویس AI تنظیم نشده است. حداقل یک API Key در Render قرار بده."
        )

    original_prompt = prompt
    try:
        _extract_and_store_memory(user_id, original_prompt)
    except Exception:
        pass

    live_shopping = await _live_shopping_prefetch(original_prompt)
    provider_prompt = original_prompt
    if live_shopping:
        provider_prompt = (
            original_prompt
            + "\n\n[SHOPPING_LIVE_RESULT]\n"
            + live_shopping[:12000]
            + "\n[/SHOPPING_LIVE_RESULT]\n"
            + "برای اطلاعات خرید فقط از داده زنده بالا استفاده کن و قیمت/موجودی جدید از خودت نساز."
        )
    # ساخت لیست (provider, model) برای امتحان — سریع‌ترین‌ها اول
    def _models_of(provider: str) -> List[Tuple[str, str]]:
        return [(provider, m) for m in models_for_provider(provider)]

    async with _LOCKS[user_id]:
        selected = get_selected_model(user_id)
        ordered: List[Tuple[str, str]] = []
        tried: set = set()
        errors: List[str] = []

        # ۱) اگر کاربر ارائه‌دهنده انتخاب کرده → همه مدل‌های همان ارائه‌دهنده
        if selected:
            provider, model = selected
            available_for_selected = _models_of(provider)
            if model == "*" or model is None:
                ordered.extend(available_for_selected)
            else:
                # اگر مدل قدیمی حذف شده باشد، آن را کورکورانه صدا نزن؛
                # اول نزدیک‌ترین مدل فعال همان provider را امتحان کن.
                if (provider, model) in available_for_selected:
                    ordered.append((provider, model))
                ordered.extend(
                    item for item in available_for_selected if item not in ordered
                )

        # ۲) بقیه ارائه‌دهنده‌ها (fallback) به ترتیب پیش‌فرض
        for provider, _label, model in options:
            item = (provider, model)
            if item not in ordered:
                ordered.append(item)

        for provider, model in ordered:
            key = (provider, model)
            if key in tried:
                continue
            tried.add(key)
            try:
                answer = await _call_provider(provider, user_id, prompt, model)
                _save_turn(user_id, original_prompt, answer)
                # اگر هنوز provider انتخاب نشده، همین را ذخیره کن (با *)
                if not selected:
                    set_selected_model(user_id, provider, "*")
                return answer, f"{provider} / {model}"
            except Exception as exc:
                msg = str(exc).replace("\n", " ")[:500]
                errors.append(f"{provider}/{model}: {msg}")
                logger.warning("AI provider/model failed: %s", msg)
                # تأخیر خیلی کم بین تلاش‌ها برای سرعت بیشتر
                await asyncio.sleep(0.05)

    if live_shopping and "نتیجه قابل‌تأییدی پیدا نشد" not in live_shopping and "نتیجه قابل‌تأیید از منابع زنده برنگشت" not in live_shopping:
        logger.warning("all AI providers failed; returning live shopping result directly")
        return live_shopping, "Live Shopping"

    raise RuntimeError(
        "فعلاً هیچ‌کدام از مدل‌های AI پاسخ ندادند.\n\n" + "\n".join(errors[:8])
    )

def _looks_like_shopping_request(text: str) -> bool:
    t = str(text or '').lower()
    return bool(__import__('re').search(r"گوشی|موبایل|لپ.?تاپ|لپتاپ|کفش|لباس|هدفون|هندزفری|تلویزیون|لوازم|محصول|خرید|قیمت|بودجه|تا\s*\d+\s*(?:میلیون|م)|amazon|آمازون|ترب|دیجی.?کالا|فروشگاه", t, __import__('re').I))

async def _live_shopping_prefetch(prompt: str) -> str:
    """Shopping is independent of AI; return verified live shopping data when possible."""
    if not _looks_like_shopping_request(prompt):
        return ''
    try:
        from bot.features.market.shopping_search_live import search_shopping
        return await asyncio.wait_for(
            search_shopping(query=prompt, max_results=10),
            timeout=float(os.getenv('SHOPPING_PREFETCH_TIMEOUT', '25')),
        )
    except Exception as exc:
        logger.warning('live shopping prefetch failed: %s', exc)
        return ''

async def _stream_openai_compatible(
    provider: str,
    user_id: int,
    prompt: str,
    *,
    url: str,
    model: str,
    extra_headers=None,
):
    """ییلد تکه‌های متن از chat/completions با stream=true."""
    import json as _json

    keys = _next_keys(provider)
    if not keys:
        raise RuntimeError(f"no keys for {provider}")

    last_err = None
    for key in keys:
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        if extra_headers:
            headers.update(extra_headers)
        payload = {
            "model": model,
            "messages": _messages(user_id, prompt),
            "max_tokens": MAX_OUTPUT,
            "temperature": 0.6,
            "stream": True,
        }
        client = _get_http()
        try:
            async with client.stream("POST", url, headers=headers, json=payload) as resp:
                if resp.status_code >= 400:
                    body = (await resp.aread())[:500]
                    if _is_quota_error(resp.status_code, body):
                        _mark_key_cooldown(provider, key, daily=True)
                        last_err = f"HTTP {resp.status_code}"
                        continue
                    raise RuntimeError(f"stream HTTP {resp.status_code}: {body!r}")
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data:"):
                        data = line[5:].strip()
                    else:
                        continue
                    if data == "[DONE]":
                        break
                    try:
                        obj = _json.loads(data)
                    except Exception:
                        continue
                    choices = obj.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    piece = delta.get("content") or ""
                    if piece:
                        yield piece
            _advance_rr(provider)
            return
        except Exception as e:
            last_err = str(e)
            continue
    raise RuntimeError(last_err or "stream failed")

async def _stream_gemini(user_id: int, prompt: str, model: str):
    """استریم Gemini با streamGenerateContent?alt=sse."""
    import json as _json

    keys = _next_keys("gemini")
    if not keys:
        raise RuntimeError("no gemini keys")

    contents = []
    mem = _memory_block(user_id)
    system = SYSTEM_PROMPT + ("\n\n" + mem if mem else "")
    for role, content in _HISTORY[user_id]:
        contents.append(
            {
                "role": "model" if role == "assistant" else "user",
                "parts": [{"text": content}],
            }
        )
    contents.append({"role": "user", "parts": [{"text": prompt}]})
    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": contents,
        "generationConfig": {"maxOutputTokens": MAX_OUTPUT},
    }
    last_err = None
    for key in keys:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
            f":streamGenerateContent"
        )
        client = _get_http()
        try:
            async with client.stream(
                "POST", url, params={"key": key, "alt": "sse"}, json=payload
            ) as resp:
                if resp.status_code >= 400:
                    body = (await resp.aread())[:400]
                    if _is_quota_error(resp.status_code, body):
                        _mark_key_cooldown("gemini", key, daily=True)
                        last_err = f"HTTP {resp.status_code}"
                        continue
                    raise RuntimeError(f"gemini stream HTTP {resp.status_code}")
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if not data or data == "[DONE]":
                        continue
                    try:
                        obj = _json.loads(data)
                        parts = obj["candidates"][0]["content"]["parts"]
                        for p in parts:
                            t = p.get("text") or ""
                            if t:
                                yield t
                    except Exception:
                        continue
            _advance_rr("gemini")
            return
        except Exception as e:
            last_err = str(e)
            continue
    raise RuntimeError(last_err or "gemini stream failed")

async def ask_ai_stream(user_id: int, prompt: str):
    """
    Stable streaming facade.

    Tool-calling providers are intentionally called through the same canonical
    non-stream path as ask_ai(), then the final answer is emitted in chunks.
    This prevents partial Telegram messages when a tool call arrives mid-stream
    and keeps Gemini/OpenAI-compatible tool semantics identical.
    """
    prompt = (prompt or "").strip()
    if not prompt:
        raise RuntimeError("پیام خالی است")
    if len(prompt) > MAX_INPUT:
        prompt = prompt[:MAX_INPUT]

    original = prompt
    try:
        _extract_and_store_memory(user_id, original)
    except Exception:
        pass

    live_shopping = await _live_shopping_prefetch(original)
    provider_prompt = original
    if live_shopping:
        provider_prompt = (
            original
            + "\n\n[SHOPPING_LIVE_RESULT]\n"
            + live_shopping[:12000]
            + "\n[/SHOPPING_LIVE_RESULT]\n"
            + "برای اطلاعات خرید فقط از داده زنده بالا استفاده کن و قیمت/موجودی جدید از خودت نساز."
        )

    options = available_model_options()
    if not options:
        raise RuntimeError("هیچ سرویس AI تنظیم نشده")

    async with _LOCKS[user_id]:
        selected = get_selected_model(user_id)
        ordered: List[Tuple[str, str]] = []
        if selected:
            provider, model = selected
            for m in models_for_provider(provider):
                if model == "*" or m == model:
                    ordered.append((provider, m))
            for m in models_for_provider(provider):
                if (provider, m) not in ordered:
                    ordered.append((provider, m))
        for provider, _label, model in options:
            if (provider, model) not in ordered:
                ordered.append((provider, model))

        errors = []
        for provider, model in ordered:
            try:
                answer = await _call_provider(provider, user_id, original, model)
                if not answer:
                    raise RuntimeError("empty answer")
                _save_turn(user_id, original, answer)
                if not selected:
                    set_selected_model(user_id, provider, "*")

                # Emit bounded chunks so Telegram still appears to stream.
                chunk_size = max(80, int(os.getenv("AI_STREAM_CHUNK", "180")))
                for i in range(0, len(answer), chunk_size):
                    yield answer[i:i + chunk_size], None
                    await asyncio.sleep(0)
                yield None, f"{provider} / {model}"
                return
            except Exception as exc:
                msg = str(exc).replace("\n", " ")[:300]
                errors.append(f"{provider}/{model}: {msg}")
                logger.warning("stream facade provider failed: %s", msg)
                await asyncio.sleep(0.05)

    if live_shopping and "نتیجه قابل‌تأییدی پیدا نشد" not in live_shopping and "نتیجه قابل‌تأیید از منابع زنده برنگشت" not in live_shopping:
        logger.warning("all AI providers failed; streaming live shopping result directly")
        chunk_size = max(80, int(os.getenv("AI_STREAM_CHUNK", "180")))
        for i in range(0, len(live_shopping), chunk_size):
            yield live_shopping[i:i + chunk_size], None
            await asyncio.sleep(0)
        yield None, "Live Shopping"
        return

    raise RuntimeError("استریم ناموفق:\n" + "\n".join(errors[:8]))
