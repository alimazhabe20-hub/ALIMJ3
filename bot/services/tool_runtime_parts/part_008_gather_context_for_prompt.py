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
