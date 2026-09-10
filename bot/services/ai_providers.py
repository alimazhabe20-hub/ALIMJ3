"""AI provider implementations extracted from ai_service (V26).

This module intentionally keeps the legacy function names so ai_service.py
continues to act as a compatibility facade for existing imports.
"""
from __future__ import annotations

import asyncio
import os
import time
from typing import Optional

import httpx

from bot.logger import logger
from bot.services.ai_runtime import (
    GEMINI_SAFETY_SETTINGS, MAX_OUTPUT, TIMEOUT, _HISTORY, _provider_keys,
    _is_key_available, _key_id, _mark_key_cooldown, _is_quota_error, _next_keys,
    _advance_rr, _get_http, _record_provider, _provider_available,
)
from bot.services.ai_tools import get_tool_definitions, execute_tool
from bot.services.tool_runtime import select_capability_tool
from bot.utils.http_client import request_with_retry


def _legacy_ai_context():
    """Load facade-owned prompt/history helpers lazily to avoid circular imports."""
    from bot.services import ai_service
    return ai_service.SYSTEM_PROMPT, ai_service._messages

async def _post_json(url: str, *, headers=None, json=None, params=None) -> tuple[int, dict]:
    """POST with shared connection pool and bounded transient retries."""
    client = _get_http()
    response = await request_with_retry(
        "POST", url, headers=headers, json=json, params=params,
        timeout=httpx.Timeout(TIMEOUT, connect=5.0),
    )
    try:
        data = response.json()
    except Exception:
        data = {"raw": response.text[:1200]}
    return response.status_code, data


def _normalize_final_text(text: str) -> str:
    """Return only user-facing text, never an internal tool protocol artifact."""
    import json
    import re

    value = str(text or "").strip()
    if not value:
        raise RuntimeError("Provider returned an empty answer")

    # A few OpenAI-compatible endpoints occasionally serialize the assistant
    # protocol object into content instead of returning proper tool_calls.
    # Treat those payloads as internal, not as a message for the user.
    candidate = value.strip()
    if candidate.startswith("```") and candidate.endswith("```"):
        candidate = candidate[3:-3].strip()
        if candidate.lower().startswith("json"):
            candidate = candidate[4:].strip()

    if candidate.startswith(("{", "[")):
        try:
            obj = json.loads(candidate)
        except Exception:
            obj = None
        if isinstance(obj, dict):
            internal_keys = {
                "tool_calls", "function_call", "functionCall", "tool_call",
                "arguments", "function",
            }
            if any(k in obj for k in internal_keys):
                raise RuntimeError("Provider returned an internal tool artifact")

    # Do not surface common tool-protocol wrappers if a provider leaks them.
    if re.match(r"^\s*(?:<tool[_ -]?call>|\[tool[_ -]?call\])", value, re.I):
        raise RuntimeError("Provider returned an internal tool artifact")
    if re.search(r"(?:^|\n)\s*tool[_ -]?calls?\s*:\s*\[", value, re.I):
        raise RuntimeError("Provider returned an internal tool artifact")

    return value


def _safe_parse_tool_arguments(parse_tool_arguments, raw_arguments):
    """Parse model tool arguments without aborting the provider attempt.

    A malformed function-call payload should be reported back to the model as
    tool data so the model gets a chance to correct its arguments during the
    remaining synthesis/tool round, instead of unnecessarily triggering a
    provider fallback.
    """
    try:
        return parse_tool_arguments(raw_arguments), None
    except Exception as exc:
        return {}, f"Invalid tool arguments: {str(exc)[:500]}"


def _extract_openai(data: dict) -> str:
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError(str(data)[:900])

    message = choices[0].get("message") or {}
    content = message.get("content")

    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if text:
                    parts.append(str(text))
        content = "".join(parts)

    if not content:
        raise RuntimeError("Provider returned an empty answer")

    return _normalize_final_text(content)


# ── Provider callers with key rotation ──────────────────────────────────────

async def _gemini(
    user_id: int,
    prompt: str,
    model: str,
    *,
    use_tools: bool = True,
    max_tool_rounds: int = 2,
) -> str:
    """
    Gemini REST caller with real function-calling support.

    نسخه قبلی فقط برای Gemini از keyword injection استفاده می‌کرد، در حالی که
    registry ابزارها برای OpenAI-compatibleها واقعاً اجرا می‌شد. این نسخه هر دو
    مسیر را دارد: function calling واقعی + دادهٔ زندهٔ keyword-based به‌عنوان fallback.
    """
    keys = _next_keys("gemini")
    if not keys:
        raise RuntimeError("هیچ کلید Gemini تنظیم نشده")

    from bot.services.ai_tools import get_tool_definitions, execute_tool, parse_tool_arguments
    from bot.services.tool_runtime import select_capability_tool

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    contents = []
    for role, content in _HISTORY[user_id]:
        contents.append({
            "role": "model" if role == "assistant" else "user",
            "parts": [{"text": content}],
        })
    contents.append({"role": "user", "parts": [{"text": prompt}]})

    # OpenAI-style registry -> Gemini functionDeclarations
    gemini_tools = []
    if use_tools:
        declarations = []
        for tool in get_tool_definitions():
            fn = tool.get("function") or {}
            if fn.get("name"):
                declarations.append({
                    "name": fn["name"],
                    "description": fn.get("description", ""),
                    "parameters": fn.get(
                        "parameters",
                        {"type": "object", "properties": {}},
                    ),
                })
        if declarations:
            gemini_tools = [{"functionDeclarations": declarations}]

    errors = []
    for key in keys:
        # Keep tool capability local to this key/attempt. A Gemini key that
        # rejects/leaks function calls must not disable tools for later keys.
        tools_enabled = bool(use_tools)
        try:
            working_contents = list(contents)

            for _round in range(max_tool_rounds + 2 if tools_enabled else 1):
                payload = {
                    "systemInstruction": {"parts": [{"text": _legacy_ai_context()[0]}]},
                    "contents": working_contents,
                    "generationConfig": {"maxOutputTokens": MAX_OUTPUT},
                    "safetySettings": GEMINI_SAFETY_SETTINGS,
                }
                if tools_enabled and gemini_tools and _round < max_tool_rounds:
                    payload["tools"] = gemini_tools
                    forced_tool = select_capability_tool(prompt)
                    if forced_tool:
                        payload["toolConfig"] = {
                            "functionCallingConfig": {
                                "mode": "ANY",
                                "allowedFunctionNames": [forced_tool],
                            }
                        }

                status, data = await _post_json(
                    url, params={"key": key}, json=payload
                )

                if status >= 400:
                    if _is_quota_error(status, data):
                        text = str(data).lower()
                        daily = status == 403 or "daily" in text or "quota" in text
                        _mark_key_cooldown("gemini", key, daily=daily)
                        errors.append(f"{_key_id('gemini', key)} HTTP {status}")
                        break
                    raise RuntimeError(
                        f"Gemini HTTP {status}: {str(data)[:900]}"
                    )

                candidates = data.get("candidates") or []
                if not candidates:
                    raise RuntimeError(
                        f"Gemini پاسخ خالی داد: {str(data)[:900]}"
                    )

                content = candidates[0].get("content") or {}
                parts = content.get("parts") or []

                function_calls = [
                    p.get("functionCall") or p.get("function_call")
                    for p in parts
                    if p.get("functionCall") or p.get("function_call")
                ]

                if function_calls and tools_enabled and _round < max_tool_rounds:
                    # پاسخ مدل را عیناً به history موقت اضافه کن.
                    working_contents.append({
                        "role": "model",
                        "parts": parts,
                    })

                    response_parts = []
                    for call in function_calls:
                        name = call.get("name") or ""
                        args = call.get("args") or call.get("arguments") or {}
                        args, parse_error = _safe_parse_tool_arguments(
                            parse_tool_arguments, args
                        )
                        if parse_error:
                            result = parse_error
                        else:
                            result = await execute_tool(
                                name, args, user_id=user_id
                            )
                        call_id = (
                            call.get("id")
                            or call.get("callId")
                            or call.get("call_id")
                            or f"call_{_round}_{name}"
                        )
                        response_parts.append({
                            "functionResponse": {
                                "name": name,
                                "id": call_id,
                                "response": {"result": result},
                            }
                        })

                    if response_parts:
                        working_contents.append({
                            "role": "user",
                            "parts": response_parts,
                        })
                        continue

                # If Gemini leaks another functionCall after the allowed tool
                # rounds, do not expose the protocol artifact or immediately
                # fall back to another provider. Force one clean, no-tools
                # synthesis turn so the current provider can turn the gathered
                # tool data into a normal user-facing answer.
                if function_calls and _round < max_tool_rounds + 1:
                    working_contents.append({
                        "role": "model",
                        "parts": parts,
                    })
                    working_contents.append({
                        "role": "user",
                        "parts": [{
                            "text": (
                                "Provide the final answer to the user now. "
                                "Do not call any function or expose tool/function "
                                "protocol. Use the tool results already available "
                                "in this conversation and answer naturally and concisely."
                            )
                        }],
                    })
                    tools_enabled = False
                    continue

                text = "".join(
                    p.get("text", "")
                    for p in parts
                    if isinstance(p, dict)
                ).strip()

                if not text:
                    raise RuntimeError(
                        f"Gemini پاسخ متنی خالی داد: {str(data)[:700]}"
                    )

                text = _normalize_final_text(text)
                _advance_rr("gemini")
                return text

        except RuntimeError as exc:
            errors.append(str(exc)[:300])
            continue
        except Exception as exc:
            errors.append(str(exc)[:300])
            continue

    raise RuntimeError(
        "همه کلیدهای Gemini تمام/خطا: " + " | ".join(errors[:5])
    )


async def _openai_compatible(
    name: str,
    provider: str,
    user_id: int,
    prompt: str,
    *,
    url: str,
    model: str,
    extra_headers=None,
    use_tools: bool = True,
) -> str:
    from bot.services.ai_tools import (
        get_tool_definitions,
        execute_tool,
        parse_tool_arguments,
    )

    keys = _next_keys(provider)
    if not keys:
        raise RuntimeError(f"هیچ کلید {name} تنظیم نشده")

    errors = []
    for key in keys:
        # Keep tool capability local to this key/attempt; one incompatible endpoint
        # must not disable tools for every fallback provider key.
        tools_enabled = bool(use_tools)
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        if extra_headers:
            headers.update(extra_headers)

        messages = _legacy_ai_context()[1](user_id, prompt)
        # حداکثر ۲ دور tool calling تا گیر نکند
        max_tool_rounds = 2 if tools_enabled else 0
        # یک دور اضافه فقط برای synthesis نهایی است؛ اگر مدل در آخرین دور
        # دوباره tool-call بدهد، نتیجه ابزار را می‌گیرد و پاسخ طبیعی را می‌سازد.
        total_rounds = max_tool_rounds + 5 if tools_enabled else 4

        try:
            for _round in range(total_rounds):
                payload = {
                    "model": model,
                    "messages": messages,
                    "max_tokens": MAX_OUTPUT,
                    "temperature": 0.6,
                }
                if tools_enabled and _round < max_tool_rounds:
                    tools = get_tool_definitions()
                    if tools:
                        payload["tools"] = tools
                        forced_tool = select_capability_tool(prompt)
                        if forced_tool:
                            payload["tool_choice"] = {
                                "type": "function",
                                "function": {"name": forced_tool},
                            }
                        else:
                            payload["tool_choice"] = "auto"

                status, data = await _post_json(url, headers=headers, json=payload)
                if status >= 400:
                    # بعضی مدل‌ها tools را پشتیبانی نمی‌کنند → بدون tool دوباره امتحان
                    err_text = str(data).lower()
                    if tools_enabled and "tool_choice" in err_text and payload.get("tools"):
                        # بعضی endpointها tools را می‌پذیرند ولی tool_choice اجباری را نه؛
                        # در این حالت ابزارها را نگه می‌داریم و به انتخاب خودکار برمی‌گردیم.
                        payload["tool_choice"] = "auto"
                        status, data = await _post_json(
                            url, headers=headers, json=payload
                        )
                    elif tools_enabled and any(
                        marker in err_text
                        for marker in (
                            "tool_calls", "tool call",
                            "function calling", "function_call",
                            "function calls", "unsupported parameter",
                        )
                    ):
                        tools_enabled = False
                        payload.pop("tools", None)
                        payload.pop("tool_choice", None)
                        status, data = await _post_json(
                            url, headers=headers, json=payload
                        )
                    if status >= 400:
                        if _is_quota_error(status, data):
                            daily = (
                                "daily" in str(data).lower()
                                or "quota" in str(data).lower()
                                or status == 403
                            )
                            _mark_key_cooldown(
                                provider, key, daily=daily or status == 429
                            )
                            errors.append(f"{_key_id(provider, key)} HTTP {status}")
                            break
                        raise RuntimeError(
                            f"{name} HTTP {status}: {str(data)[:900]}"
                        )

                choices = data.get("choices") or []
                if not choices:
                    raise RuntimeError(str(data)[:900])

                message = choices[0].get("message") or {}
                tool_calls = message.get("tool_calls") or []

                if tool_calls and tools_enabled and _round < max_tool_rounds:
                    # پاسخ assistant با tool_calls را به تاریخچه اضافه کن
                    messages.append(message)
                    for tc in tool_calls:
                        fn = tc.get("function") or {}
                        fname = fn.get("name") or ""
                        fargs, parse_error = _safe_parse_tool_arguments(
                            parse_tool_arguments, fn.get("arguments")
                        )
                        if parse_error:
                            result = parse_error
                        else:
                            result = await execute_tool(
                                fname, fargs, user_id=user_id
                            )
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tc.get("id") or fname,
                                "content": result,
                            }
                        )
                    continue  # دور بعد با نتایج tool

                # Some OpenAI-compatible models may emit a tool-call-shaped
                # message even when tools are no longer being offered. Do not
                # surface that internal protocol object as an empty/raw reply.
                # Keep the assistant message, disable tools for this attempt,
                # and use the next synthesis round to obtain plain text.
                if tool_calls and _round < total_rounds - 1:
                    messages.append(message)
                    tools_enabled = False
                    continue

                text = _extract_openai(data)
                finish_reason = str((choices[0] or {}).get("finish_reason") or "").lower()
                # اگر مدل به سقف خروجی رسیده، همان‌جا پاسخ را تحویل نده؛
                # چند دور ادامهٔ خودکار می‌گیریم تا پاسخ واقعاً کامل شود.
                if finish_reason in {"length", "max_tokens", "max_output_tokens"} and text and _round < total_rounds - 1:
                    messages.append({"role": "assistant", "content": text})
                    messages.append({
                        "role": "user",
                        "content": (
                            "پاسخ قبلی به سقف خروجی رسید. دقیقاً از همان نقطه ادامه بده. "
                            "هیچ بخش قبلی را تکرار نکن، مقدمه نده و فقط ادامهٔ طبیعی پاسخ را بنویس. "
                            "اگر یک بخش/جدول/فهرست نیمه‌تمام است ابتدا همان را کامل کن."
                        ),
                    })
                    continue
                _advance_rr(provider)
                return text

            # اگر از حلقه key بیرون آمدیم بدون return
            continue
        except RuntimeError as exc:
            msg = str(exc)
            if _is_quota_error(0, msg) or "429" in msg or "403" in msg:
                _mark_key_cooldown(provider, key, daily=True)
            errors.append(msg[:200])
            continue

    raise RuntimeError(f"همه کلیدهای {name} تمام/خطا: " + " | ".join(errors[:5]))


async def _groq(user_id: int, prompt: str, model: str) -> str:
    return await _openai_compatible(
        "Groq",
        "groq",
        user_id,
        prompt,
        url=os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
        + "/chat/completions",
        model=model,
    )


async def _cerebras(user_id: int, prompt: str, model: str) -> str:
    return await _openai_compatible(
        "Cerebras",
        "cerebras",
        user_id,
        prompt,
        url="https://api.cerebras.ai/v1/chat/completions",
        model=model,
    )


async def _openrouter(user_id: int, prompt: str, model: str) -> str:
    return await _openai_compatible(
        "OpenRouter",
        "openrouter",
        user_id,
        prompt,
        url="https://openrouter.ai/api/v1/chat/completions",
        model=model,
        extra_headers={"X-Title": "Rooze Ziba"},
    )


async def _cloudflare(user_id: int, prompt: str, model: str) -> str:
    account = os.getenv("CLOUDFLARE_ACCOUNT_ID")
    if not account:
        raise RuntimeError("CLOUDFLARE_ACCOUNT_ID تنظیم نشده")
    keys = _next_keys("cloudflare")
    if not keys:
        raise RuntimeError("هیچ توکن Cloudflare تنظیم نشده")

    url = f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{model}"
    payload = {
        "messages": _legacy_ai_context()[1](user_id, prompt),
        "max_tokens": MAX_OUTPUT,
    }

    errors = []
    for token in keys:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        try:
            status, data = await _post_json(url, headers=headers, json=payload)
            if status >= 400 or not data.get("success", True):
                if _is_quota_error(status, data):
                    _mark_key_cooldown("cloudflare", token, daily=True)
                    errors.append(f"{_key_id('cloudflare', token)} HTTP {status}")
                    continue
                raise RuntimeError(f"Cloudflare HTTP {status}: {str(data)[:900]}")

            result = data.get("result") or {}
            text = result.get("response") or result.get("text")
            if not text:
                raise RuntimeError(f"Cloudflare empty response: {str(data)[:900]}")
            text = _normalize_final_text(str(text))
            _advance_rr("cloudflare")
            return text
        except RuntimeError as exc:
            errors.append(str(exc)[:200])
            continue

    raise RuntimeError("همه توکن‌های Cloudflare تمام/خطا: " + " | ".join(errors[:5]))


async def _call_provider(provider: str, user_id: int, prompt: str, model: str) -> str:
    if provider == "gemini":
        return await _gemini(user_id, prompt, model)
    if provider == "groq":
        return await _groq(user_id, prompt, model)
    if provider == "cerebras":
        return await _cerebras(user_id, prompt, model)
    if provider == "cloudflare":
        return await _cloudflare(user_id, prompt, model)
    if provider == "openrouter":
        return await _openrouter(user_id, prompt, model)
    raise RuntimeError(f"Unknown AI provider: {provider}")



