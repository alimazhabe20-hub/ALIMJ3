from typing import Any

# Auto-split part 13: dedupe_sources
def dedupe_sources(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen, out = set(), []
    for item in items:
        try: key = safe_web_url(item.get("url", ""))
        except Exception: continue
        domain = (urlparse(key).hostname or "").lower()
        if key in seen: continue
        seen.add(key)
        score = float(item.get("score") or 0)
        if domain.endswith("wikipedia.org"): score += .15
        if key.startswith("https://"): score += .05
        out.append({**item, "url": key, "domain": domain, "score": round(min(1.0, score), 4)})
    return sorted(out, key=lambda x: (-x["score"], x["domain"]))[:20]
