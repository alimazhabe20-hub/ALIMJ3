"""AI tool registry and execution runtime.

Built-in handlers remain in ai_tools.py; this module owns the generic runtime
so adding tools does not require growing the execution engine.
"""

# BEGIN MERGED LEGACY PART: tool_runtime_parts/part_001_register_tool.py
from typing import Callable
from typing import List
from typing import Optional

# Auto-split part 1: register_tool
def register_tool(
    name: str,
    description: str,
    parameters: Optional[dict] = None,
    handler: Optional[Callable] = None,
    *,
    keywords: Optional[List[str]] = None,
    risk: str = "read",
    network: bool = False,
) -> None:
    """ثبت یک ابزار برای AI. keywords برای تزریق خودکار وقتی مدل tool ندارد."""
    if not name or not handler:
        raise ValueError("name و handler الزامی‌اند")
    _REGISTRY[name] = {
        "name": name,
        "description": description,
        "parameters": parameters or {"type": "object", "properties": {}},
        "handler": handler,
        "keywords": keywords or [],
        "cacheable": False,
        "risk": risk if risk in {"read", "write", "admin"} else "read",
        "network": bool(network),
    }
    logger.debug("AI tool registered: %s", name)

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: tool_runtime_parts/part_002_get_registered_tool_names.py
# Auto-split part 2: get_registered_tool_names
def get_registered_tool_names() -> set[str]:
    """Return a snapshot of registered tool names for workflow validation."""
    return set(_REGISTRY)

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: tool_runtime_parts/part_003_get_tool_definitions.py
from typing import List

# Auto-split part 3: get_tool_definitions
def get_tool_definitions() -> List[dict]:
    """لیست tools به فرمت OpenAI/Groq."""
    out = []
    for t in _REGISTRY.values():
        out.append(
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["parameters"],
                },
            }
        )
    return out

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: tool_runtime_parts/part_004_parse_tool_arguments.py
from typing import Any

# Auto-split part 4: parse_tool_arguments
def parse_tool_arguments(raw: Any) -> dict:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw) if raw.strip() else {}
        except Exception:
            return {}
    return {}

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: tool_runtime_parts/part_005_execute_tool.py
# Auto-split part 5: execute_tool
async def execute_tool(name: str, arguments: dict, *, user_id: int = 0, source: str = "system", approved: bool = False) -> str:
    entry = _REGISTRY.get(name)
    if not entry:
        return f"ابزار ناشناخته: {name}"
    handler = entry["handler"]
    if entry.get("risk") in {"write", "admin"} and source in {"agent", "agent_repair"} and not approved:
        return f"ابزار مسدود: {name} نیاز به تأیید صریح دارد."
    try:
        from bot.services.v74_platform import tool_allowed, note_failure as v74_note_failure, recover_component as v74_recover_component, record_performance as v74_record_performance, register_tool_policy
        allowed_v74, reason_v74 = tool_allowed(name, source=source, approved=approved)
        if not allowed_v74:
            return f"ابزار مسدود: {name} ({reason_v74})"
        entry_v74 = _REGISTRY.get(name, {})
        register_tool_policy(name, version=str(entry_v74.get("version", "1.0")), risk=entry_v74.get("risk", "read"), network=bool(entry_v74.get("network", False)))
    except Exception:
        v74_note_failure = None
        v74_recover_component = None
        v74_record_performance = None

    try:
        from bot.services.v73_platform import component_available, note_failure, recover_component, record_performance
        if not component_available(f"tool:{name}"):
            return f"ابزار موقتاً در حالت محافظتی است: {name}"
    except Exception:
        record_performance = None
        note_failure = None
        recover_component = None
    args = dict(arguments or {})
    try:
        sig = inspect.signature(handler)
        if "user_id" in sig.parameters:
            args.setdefault("user_id", user_id)
        allowed = set(sig.parameters.keys())
        args = {k: v for k, v in args.items() if k in allowed}
    except Exception:
        pass

    # Cache only explicitly read-only tools; never cache reminders, writes or side effects.
    try:
        fingerprint = json.dumps([name, user_id, args], ensure_ascii=False, sort_keys=True, default=str)
    except Exception:
        fingerprint = f"{name}:{user_id}:{repr(args)}"
    if name in _TOOL_CACHEABLE:
        cached = _TOOL_CACHE.get((name, user_id, fingerprint))
        if cached and cached[0] > time.monotonic():
            return cached[1]
        _TOOL_CACHE.pop((name, user_id, fingerprint), None)

    async with _TOOL_INFLIGHT_LOCK:
        task = _TOOL_INFLIGHT.get(fingerprint)
        if task is None or task.done():
            async def _run():
                try:
                    async with _TOOL_SEMAPHORE:
                        _started = time.monotonic()
                        if inspect.iscoroutinefunction(handler):
                            result = await asyncio.wait_for(handler(**args), timeout=_TOOL_TIMEOUT)
                        else:
                            result = await asyncio.wait_for(asyncio.to_thread(handler, **args), timeout=_TOOL_TIMEOUT)
                    text = str(result)[:4500] if result is not None else "نتیجه‌ای برنگشت."
                    if record_performance:
                        record_performance(name, (time.monotonic() - _started) * 1000, True)
                    record_metric("ai_tool", name, ok=True, latency=time.monotonic() - _started)
                    if name in _TOOL_CACHEABLE:
                        # Keep the read-through cache bounded even on long-running bots.
                        now = time.monotonic()
                        _TOOL_CACHE[(name, user_id, fingerprint)] = (now + _TOOL_CACHE_TTL, text)
                        if len(_TOOL_CACHE) > 1024:
                            stale = [k for k, (expires, _) in _TOOL_CACHE.items() if expires <= now]
                            for k in stale[:512]:
                                _TOOL_CACHE.pop(k, None)
                            if len(_TOOL_CACHE) > _TOOL_CACHE_MAX:
                                overflow = len(_TOOL_CACHE) - _TOOL_CACHE_MAX
                                for k in list(_TOOL_CACHE)[:overflow]:
                                    _TOOL_CACHE.pop(k, None)
                    return text
                except asyncio.TimeoutError:
                    if record_performance:
                        record_performance(name, (time.monotonic() - _started) * 1000, False)
                    if note_failure and note_failure(f"tool:{name}"):
                        try:
                            recover_component(f"tool:{name}")
                        except Exception:
                            pass
                    record_metric("ai_tool", name, ok=False, latency=time.monotonic() - _started)
                    logger.warning("tool %s timed out after %ss", name, _TOOL_TIMEOUT)
                    return f"زمان اجرای {name} تمام شد؛ دوباره تلاش کن."
                except Exception as e:
                    if record_performance:
                        record_performance(name, (time.monotonic() - _started) * 1000, False)
                    if note_failure and note_failure(f"tool:{name}"):
                        try:
                            recover_component(f"tool:{name}")
                        except Exception:
                            pass
                    record_metric("ai_tool", name, ok=False, latency=time.monotonic() - _started)
                    logger.warning("tool %s failed: %s", name, e, exc_info=True)
                    return f"خطا در اجرای {name}: {e}"
            from bot.utils.task_manager import spawn
            task = spawn(_run(), name=f"ai-tool-{name}")
            _TOOL_INFLIGHT[fingerprint] = task
    try:
        return await task
    finally:
        if task.done():
            async with _TOOL_INFLIGHT_LOCK:
                if _TOOL_INFLIGHT.get(fingerprint) is task:
                    _TOOL_INFLIGHT.pop(fingerprint, None)

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: tool_runtime_parts/part_006_select_capability_tool.py
from typing import Optional

# Auto-split part 6: select_capability_tool
def select_capability_tool(prompt: str) -> Optional[str]:
    """انتخاب ابزار فقط وقتی تطبیق به‌اندازه کافی قوی و غیرمبهم باشد.

    امتیازدهی چندمرحله‌ای است: عبارت‌های بلندتر و تطبیق‌های چندکلمه‌ای وزن بیشتری
    دارند. اگر دو قابلیت هم‌زمان امتیاز نزدیک داشته باشند، هیچ ابزاری به‌صورت اجباری
    انتخاب نمی‌شود تا مدل بتواند درخواست چندبخشی را با چند Tool مدیریت کند.
    """
    text = _normalize_capability_text(prompt)
    if not text:
        return None

    # Deterministic high-priority routing for capabilities whose answer must come
    # from a real subsystem (date/time, latest catalog, live market, ...).
    try:
        from bot.services.ai_capability_router import route_live_capability
        live_tool = route_live_capability(text)
        if live_tool and live_tool in _REGISTRY:
            return live_tool
    except Exception as exc:
        logger.debug("capability router unavailable: %s", exc)

    # Time-sensitive requests must never fall back to model memory.  Prefer the
    # live product search for shopping requests; otherwise force a web/live tool.
    try:
        from bot.services.ai_freshness import classify
        freshness = classify(text)
        if freshness.required:
            if freshness.tool and freshness.tool in _REGISTRY:
                return freshness.tool
            if "web_search" in _REGISTRY:
                # Market/weather tools have their own live handlers and should win
                # when their registry score is clearly specific.
                live_specific = []
                for name, entry in _REGISTRY.items():
                    if name == "web_search":
                        continue
                    score = 0.0
                    for kw in entry.get("keywords") or []:
                        try:
                            m = re.search(kw, text, re.I)
                        except re.error:
                            continue
                        if m:
                            score += 1.0 + min(len(m.group(0)), 64) / 16.0
                    if score:
                        live_specific.append((score, name))
                live_specific.sort(reverse=True)
                if live_specific and live_specific[0][0] >= 1.0:
                    return live_specific[0][1]
                return "web_search"
    except Exception as exc:
        logger.debug("freshness router unavailable: %s", exc)

    # No dedicated capability matched: use keyless API Hub first, then web.
    try:
        from bot.services.ai_capability_router import route_with_fallback
        fallback_tool = route_with_fallback(text)
        if fallback_tool and fallback_tool in _REGISTRY:
            return fallback_tool
    except Exception as exc:
        logger.debug("generic capability fallback unavailable: %s", exc)

    ranked = []
    for name, entry in _REGISTRY.items():
        score = 0.0
        hits = 0
        longest = 0
        for kw in entry.get("keywords") or []:
            try:
                m = re.search(kw, text, re.I)
            except re.error:
                continue
            if not m:
                continue
            matched = (m.group(0) or kw).strip()
            length = len(re.sub(r"\\s+", "", matched))
            # تطبیق‌های مشخص‌تر از keywordهای عمومی مثل «قیمت» مهم‌ترند.
            score += 1.0 + min(length, 64) / 16.0
            hits += 1
            longest = max(longest, length)

        if not hits:
            continue
        if name == "run_agent" and score < 2.0:
            continue
        ranked.append((score, hits, longest, name))

    if not ranked:
        return None

    ranked.sort(reverse=True)
    best = ranked[0]
    if len(ranked) > 1:
        second = ranked[1]
        # درخواست‌های چندقابلیتی را به یک Tool قفل نکن.
        if (best[0] < second[0] * 1.10 and
                best[2] <= second[2] + 2 and
                best[1] <= second[1] + 1):
            return None
        # اگر دو قابلیت متفاوت در یک درخواست با «و» حضور دارند، یک Tool را force نکن.
        if second[3] != best[3] and second[0] >= 1.25 and re.search(r"\sو\s", text):
            return None

    # تطبیق تک‌کلمه‌ای ضعیف، به‌تنهایی مجوز force کردن Tool نیست.
    if best[0] < 1.25 or (best[2] < 5 and len(text.split()) <= 1):
        return None
    if best[2] == 5 and len(text.split()) <= 1:
        return None
    return best[3]

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: tool_runtime_parts/part_007__normalize_capability_text.py
# Auto-split part 7: _normalize_capability_text
def _normalize_capability_text(text: str) -> str:
    """نرمال‌سازی سبک برای Router بدون تغییر متن اصلی ارسالی به مدل."""
    text = (text or "").strip().lower()
    text = text.replace("ي", "ی").replace("ك", "ک")
    text = re.sub(r"[ـ‌‍]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: tool_runtime_parts/part_008_gather_context_for_prompt.py
# Auto-split part 8: gather_context_for_prompt
async def gather_context_for_prompt(user_id: int, prompt: str) -> str:
    """
    Compatibility fallback for providers that do not support function calling.

    IMPORTANT: never execute a tool that has required arguments with ``{}``.
    That old behaviour could silently call tools with invalid parameters and
    inject unrelated data into the prompt. Only zero-argument tools are safe
    to prefetch here. Providers with native function calling should use the
    registry directly instead.
    """
    text = (prompt or "").strip()
    if not text:
        return ""

    chunks: List[str] = []
    used = set()
    for name, entry in _REGISTRY.items():
        if name in used:
            continue
        kws = entry.get("keywords") or []
        if not kws:
            continue
        params = entry.get("parameters") or {}
        required = params.get("required") or []
        if required:
            continue
        for kw in kws:
            try:
                if re.search(kw, text, re.I):
                    result = await execute_tool(name, {}, user_id=user_id)
                    if result and not str(result).startswith("خطا") and not str(result).startswith("ابزار ناشناخته"):
                        chunks.append(f"[{name}]\n{result}")
                        used.add(name)
                    break
            except Exception as e:
                logger.warning("gather_context %s: %s", name, e)

    if not chunks:
        return ""
    return (
        "\n\n[دادهٔ زنده از قابلیت‌های ربات — فقط از این اطلاعات برای اعداد و وضعیت واقعی استفاده کن]\n"
        + "\n---\n".join(chunks[:6])
    )

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: tool_runtime_parts/part_009_list_registered_tools.py
from typing import List

# Auto-split part 9: list_registered_tools
def list_registered_tools() -> List[str]:
    return sorted(_REGISTRY.keys())

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: tool_runtime_parts/part_010_clear_tool_cache.py
# Auto-split part 10: clear_tool_cache
def clear_tool_cache() -> None:
    """Clear read-through tool cache without touching tool registry/state."""
    _TOOL_CACHE.clear()

# END MERGED LEGACY PART: 
import inspect
import json
import re
import asyncio
import os
import time
from typing import Any, Callable, Dict, List, Optional
from bot.logger import logger
from bot.utils.observability import record as record_metric

_REGISTRY: Dict[str, dict] = {}
_TOOL_INFLIGHT: Dict[str, asyncio.Task] = {}
_TOOL_INFLIGHT_LOCK = asyncio.Lock()
_TOOL_SEMAPHORE = asyncio.Semaphore(max(2, int(os.getenv("AI_TOOL_CONCURRENCY", "8"))))
_TOOL_CACHE: Dict[tuple, tuple[float, str]] = {}
_TOOL_CACHE_TTL = max(5, int(os.getenv("AI_TOOL_CACHE_TTL", "20")))
_TOOL_TIMEOUT = max(5.0, float(os.getenv("AI_TOOL_TIMEOUT", "25")))
_TOOL_CACHE_MAX = max(64, int(os.getenv("AI_TOOL_CACHE_MAX", "1024")))
_TOOL_CACHEABLE = {
    "get_weather", "get_weather_forecast", "get_air_quality",
    "get_market_prices", "get_top_crypto", "get_user_city", "get_economic_calendar",
    "analyze_gold", "get_current_datetime", "get_crypto_price",
}


# ── Auto-connect: ensure full capability set is visible to the model ─────────
def _ensure_caps() -> None:
    try:
        from bot.services.capability_autoload import _ENSURING, ensure_all_capabilities_registered
        # Registration itself calls registry helpers. Do not re-enter the
        # autoloader while it is already registering capabilities.
        if _ENSURING:
            return
        ensure_all_capabilities_registered()
    except Exception as exc:
        logger.debug("tool_runtime ensure caps: %s", exc)


_orig_get_tool_definitions = get_tool_definitions  # noqa: F821 — loaded above
_orig_execute_tool = execute_tool  # noqa: F821
_orig_get_registered_tool_names = get_registered_tool_names  # noqa: F821


def get_tool_definitions(*args, **kwargs):
    _ensure_caps()
    return _orig_get_tool_definitions(*args, **kwargs)


async def execute_tool(*args, **kwargs):
    _ensure_caps()
    return await _orig_execute_tool(*args, **kwargs)


def get_registered_tool_names(*args, **kwargs):
    _ensure_caps()
    return _orig_get_registered_tool_names(*args, **kwargs)
tool_runtime_parts/part_001_register_tool.py
tool_runtime_parts/part_002_get_registered_tool_names.py
tool_runtime_parts/part_003_get_tool_definitions.py
tool_runtime_parts/part_004_parse_tool_arguments.py
tool_runtime_parts/part_005_execute_tool.py
tool_runtime_parts/part_006_select_capability_tool.py
tool_runtime_parts/part_007__normalize_capability_text.py
tool_runtime_parts/part_008_gather_context_for_prompt.py
tool_runtime_parts/part_009_list_registered_tools.py
tool_runtime_parts/part_010_clear_tool_cache.py
