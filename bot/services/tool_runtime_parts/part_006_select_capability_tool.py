from typing import Optional

# Auto-split part 6: select_capability_tool

def select_capability_tool(prompt: str) -> Optional[str]:
    """Select a capability only when the match is strong and unambiguous.

    Freshness-sensitive requests are special: web_search is forced so the model
    cannot silently answer from stale training knowledge.
    """
    text = _normalize_capability_text(prompt)
    if not text:
        return None

    # Hard freshness gate. Keep this before the generic keyword ranking so a
    # current product/price/news question cannot fall through to plain chat.
    try:
        from bot.services.ai_freshness import requires_live_shopping, requires_live_web
        if requires_live_shopping(text):
            return "search_shopping"
        if requires_live_web(text):
            return "web_search"
    except Exception:
        # Router must remain backward-compatible if the optional policy module
        # is temporarily unavailable.
        pass

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
        if (best[0] < second[0] * 1.10 and
                best[2] <= second[2] + 2 and
                best[1] <= second[1] + 1):
            return None
        if second[3] != best[3] and second[0] >= 1.25 and re.search(r"\sو\s", text):
            return None

    if best[0] < 1.25 or (best[2] < 5 and len(text.split()) <= 1):
        return None
    if best[2] == 5 and len(text.split()) <= 1:
        return None
    return best[3]
