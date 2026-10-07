from typing import Any

# Auto-split part 12: rank_sources
def rank_sources(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set(); out = []
    for item in items or []:
        url = str(item.get("url") or "").strip()
        title = str(item.get("title") or "").strip()
        key = stable_hash(url or title.lower())
        if key in seen: continue
        seen.add(key)
        trust = float(item.get("trust", 0) or 0)
        if url.startswith("https://"): trust += 0.1
        item = dict(item); item["trust_score"] = round(min(1.0, trust), 3)
        out.append(item)
    return sorted(out, key=lambda x: (-x["trust_score"], x.get("title", "")))
