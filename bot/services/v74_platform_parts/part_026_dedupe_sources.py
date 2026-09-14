from typing import Any
from typing import Iterable

# Auto-split part 26: dedupe_sources
def dedupe_sources(sources: Iterable[dict[str, Any]], limit: int = 20) -> list[dict[str, Any]]:
    seen: set[str] = set(); out: list[dict[str, Any]] = []
    for item in sources:
        url = str(item.get("url") or "").strip()
        ok, _ = safe_public_url(url)
        if not ok or url in seen: continue
        seen.add(url)
        text = sanitize_untrusted_text(str(item.get("text") or ""), 16000)
        out.append({**item, "url": url, "text": text, "score": source_score(url, text, float(item.get("score") or .4))})
    return sorted(out, key=lambda x: (-x["score"], x["url"]))[:max(1, min(limit, 50))]
