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
