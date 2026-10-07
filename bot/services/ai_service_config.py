"""ai_service: config responsibilities."""
from .ai_service_common import *  # noqa: F401,F403
from . import ai_service_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


def _get_http() -> httpx.AsyncClient:
    global _HTTP
    if _HTTP is None or _HTTP.is_closed:
        _HTTP = httpx.AsyncClient(
            timeout=httpx.Timeout(TIMEOUT, connect=5.0),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=40),
            http2=False,
        )
    return _HTTP

async def close_http() -> None:
    """بستن کلاینت HTTP در shutdown ربات."""
    global _HTTP
    if _HTTP is not None and not _HTTP.is_closed:
        await _HTTP.aclose()
    _HTTP = None

def _split_keys(*env_names: str) -> List[str]:
    """از یک یا چند env، کلیدها را با کاما جدا می‌کند."""
    keys: List[str] = []
    seen = set()
    for name in env_names:
        raw = os.getenv(name, "") or ""
        for part in raw.replace(";", ",").split(","):
            k = part.strip()
            if k and k not in seen:
                seen.add(k)
                keys.append(k)
    return keys

def _provider_keys(provider: str) -> List[str]:
    if provider == "gemini":
        return _split_keys("GEMINI_API_KEY", "GEMINI_API_KEYS")
    if provider == "groq":
        return _split_keys("GROQ_API_KEY", "GROQ_API_KEYS")
    if provider == "cerebras":
        return _split_keys("CEREBRAS_API_KEY", "CEREBRAS_API_KEYS")
    if provider == "openrouter":
        return _split_keys("OPENROUTER_API_KEY", "OPENROUTER_API_KEYS")
    if provider == "cloudflare":
        # برای کلودفلر توکن‌ها؛ اکانت معمولاً یکی است
        return _split_keys("CLOUDFLARE_AUTH_TOKEN", "CLOUDFLARE_AUTH_TOKENS")
    return []

def _key_id(provider: str, key: str) -> str:
    # فقط چند کاراکتر آخر برای لاگ امن
    tail = key[-6:] if len(key) >= 6 else key
    return f"{provider}:{tail}"

def _is_key_available(kid: str) -> bool:
    until = _KEY_COOLDOWN.get(kid, 0)
    if until <= time.time():
        _KEY_COOLDOWN.pop(kid, None)
        return True
    return False

def _mark_key_cooldown(provider: str, key: str, *, daily: bool = True) -> None:
    kid = _key_id(provider, key)
    sec = KEY_COOLDOWN_SEC if daily else KEY_SHORT_COOLDOWN_SEC
    _KEY_COOLDOWN[kid] = time.time() + sec
    logger.warning(
        "AI key cooldown: %s for %ss (daily=%s)", kid, sec, daily
    )

def _is_quota_error(status: int, data) -> bool:
    """تشخیص محدودیت روزانه / سهمیه / rate limit."""
    if status in (429, 403):
        return True
    text = str(data).lower()
    markers = (
        "quota",
        "rate limit",
        "rate_limit",
        "resource exhausted",
        "resource_exhausted",
        "too many requests",
        "exceeded",
        "limit exceeded",
        "daily limit",
        "usage limit",
        "insufficient_quota",
        "tokens per day",
        "tpm",
        "rpm",
    )
    return any(m in text for m in markers)

def _next_keys(provider: str) -> List[str]:
    """
    لیست کلیدهای قابل استفاده به ترتیب round-robin.
    کلیدهای در حال cooldown آخر می‌آیند (اگر همه تمام باشند باز هم امتحان می‌شوند).
    """
    keys = _provider_keys(provider)
    if not keys:
        return []
    n = len(keys)
    start = _KEY_RR[provider] % n
    ordered = keys[start:] + keys[:start]
    available = [k for k in ordered if _is_key_available(_key_id(provider, k))]
    cooled = [k for k in ordered if not _is_key_available(_key_id(provider, k))]
    return available + cooled

def _advance_rr(provider: str) -> None:
    keys = _provider_keys(provider)
    if keys:
        _KEY_RR[provider] = (_KEY_RR[provider] + 1) % len(keys)

def clear_history(user_id: int, *, clear_long_term: bool = False) -> None:
    _HISTORY.pop(user_id, None)
    try:
        from bot.database import clear_ai_history_summary, delete_ai_memory
        clear_ai_history_summary(user_id)
        if clear_long_term:
            delete_ai_memory(user_id)
    except Exception:
        pass

def _valid_selected_model(pref: Tuple[str, str] | None) -> Tuple[str, str] | None:
    """Return a saved selection only if its provider/model still exists."""
    if not pref:
        return None
    provider, model = pref
    provider = (provider or "").strip().lower()
    model = (model or "*").strip()
    if provider not in {p for p, _label, _model in available_model_options()}:
        return None
    models = models_for_provider(provider)
    if not models:
        return None
    if model == "*" or model in models:
        return provider, model
    return provider, "*"

def get_selected_model(user_id: int) -> Tuple[str, str] | None:
    if user_id in _USER_SELECTION:
        return _USER_SELECTION[user_id]
    try:
        from bot.database import get_ai_preference
        pref = get_ai_preference(user_id)
        if pref:
            valid = _valid_selected_model(pref)
            if valid:
                _USER_SELECTION[user_id] = valid
                if valid != pref:
                    try:
                        set_ai_preference(user_id, valid[0], valid[1])
                    except Exception:
                        pass
                return valid
            clear_selected_model(user_id)
    except Exception as e:
        logger.warning("get_ai_preference failed: %s", e)
    return None

def set_selected_model(user_id: int, provider: str, model: str) -> None:
    _USER_SELECTION[user_id] = (provider, model)
    try:
        from bot.database import set_ai_preference
        set_ai_preference(user_id, provider, model)
    except Exception as e:
        logger.warning("set_ai_preference failed: %s", e)

def clear_selected_model(user_id: int) -> None:
    _USER_SELECTION.pop(user_id, None)
    try:
        from bot.database import clear_ai_preference
        clear_ai_preference(user_id)
    except Exception as e:
        logger.warning("clear_ai_preference failed: %s", e)

def _env_models(env_name: str, default: List[str]) -> List[str]:
    raw = os.getenv(env_name, "")
    values = [x.strip() for x in raw.split(",") if x.strip()]
    return values or default

def available_model_options() -> List[Tuple[str, str, str]]:
    """همه مدل‌ها به ترتیب ارائه‌دهنده و سرعت (سریع‌ترین اول)."""
    raw: Dict[str, List[Tuple[str, str, str]]] = {}

    if _provider_keys("gemini"):
        items = []
        # مدل‌های پایدار جدید؛ Lite برای سرعت، 3.6 برای کیفیت
        for model in _env_models(
            "GEMINI_MODELS",
            ["gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-3.1-flash-lite"],
        ):
            label = "Gemini • " + model.replace("gemini-", "Gemini ")
            items.append(("gemini", label, model))
        raw["gemini"] = items

    if _provider_keys("groq"):
        items = []
        # instant اول = خیلی سریع
        for model in _env_models(
            "GROQ_MODELS",
            [
                "llama-3.1-8b-instant",
                "openai/gpt-oss-20b",
                "llama-3.3-70b-versatile",
                "openai/gpt-oss-120b",
            ],
        ):
            items.append(("groq", "Groq • " + model, model))
        raw["groq"] = items

    if _provider_keys("cerebras"):
        items = []
        for model in _env_models(
            "CEREBRAS_MODELS",
            [os.getenv("CEREBRAS_MODEL", "gpt-oss-120b")],
        ):
            items.append(("cerebras", "Cerebras • " + model, model))
        raw["cerebras"] = items

    if os.getenv("CLOUDFLARE_ACCOUNT_ID") and _provider_keys("cloudflare"):
        items = []
        for model in _env_models(
            "CLOUDFLARE_MODELS",
            [os.getenv("CLOUDFLARE_MODEL", "@cf/meta/llama-3.2-3b-instruct")],
        ):
            items.append(("cloudflare", "Cloudflare • " + model, model))
        raw["cloudflare"] = items

    if _provider_keys("openrouter"):
        items = []
        for model in _env_models(
            "OPENROUTER_MODELS",
            [os.getenv("OPENROUTER_MODEL", "openrouter/free")],
        ):
            items.append(("openrouter", "OpenRouter • " + model, model))
        raw["openrouter"] = items

    ordered: List[Tuple[str, str, str]] = []
    seen = set()
    for p in _DEFAULT_ORDER:
        if p in raw and p not in seen:
            ordered.extend(raw[p])
            seen.add(p)
    for p, items in raw.items():
        if p not in seen:
            ordered.extend(items)
    return ordered

def available_providers() -> List[Tuple[str, str]]:
    """
    لیست ارائه‌دهنده‌های فعال برای دکمهٔ انتخاب.
    هر آیتم: (provider_id, label)
    با انتخاب یک ارائه‌دهنده، همه مدل‌هایش به‌صورت خودکار امتحان می‌شوند.
    """
    options = available_model_options()
    by_provider: Dict[str, int] = {}
    for provider, _label, _model in options:
        by_provider[provider] = by_provider.get(provider, 0) + 1

    result: List[Tuple[str, str]] = []
    seen = set()
    for p in _DEFAULT_ORDER:
        if p in by_provider and p not in seen:
            pretty = _PROVIDER_PRETTY.get(p, p)
            n = by_provider[p]
            keys = len(_provider_keys(p))
            suffix = f" ({n} مدل)" if n > 1 else ""
            if keys > 1:
                suffix += f" ×{keys} کلید"
            result.append((p, f"{pretty}{suffix}"))
            seen.add(p)
    for p, n in by_provider.items():
        if p not in seen:
            pretty = _PROVIDER_PRETTY.get(p, p)
            suffix = f" ({n} مدل)" if n > 1 else ""
            result.append((p, f"{pretty}{suffix}"))
    return result

def models_for_provider(provider: str) -> List[str]:
    """مدل‌های یک ارائه‌دهنده به ترتیب سرعت (اول = سریع‌تر)."""
    return [m for p, _l, m in available_model_options() if p == provider]

def enabled_providers() -> List[str]:
    return [label for _p, label in available_providers()]

def default_model_info() -> str:
    providers = available_providers()
    if not providers:
        return "هیچ"
    return providers[0][1]

def set_selected_provider(user_id: int, provider: str) -> None:
    """انتخاب ارائه‌دهنده — همه مدل‌هایش شامل می‌شوند (model='*')."""
    set_selected_model(user_id, provider, "*")

def key_pool_status() -> str:
    """برای ادمین: وضعیت کلیدها."""
    lines = []
    for provider in ("gemini", "groq", "cerebras", "openrouter", "cloudflare"):
        keys = _provider_keys(provider)
        if not keys:
            continue
        avail = sum(1 for k in keys if _is_key_available(_key_id(provider, k)))
        lines.append(f"{provider}: {avail}/{len(keys)} فعال")
    return "\n".join(lines) if lines else "هیچ کلیدی تنظیم نشده"
