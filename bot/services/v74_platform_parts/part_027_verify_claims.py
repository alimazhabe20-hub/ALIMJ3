from typing import Any
from typing import Iterable

# Auto-split part 27: verify_claims
def verify_claims(claims: Iterable[str], sources: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    srcs = dedupe_sources(list(sources), 30); results=[]
    for claim in list(claims)[:30]:
        tokens = [t.lower() for t in re.findall(r"[\w\u0600-\u06ff]{4,}", str(claim))][:14]
        evidence=[]
        for src in srcs:
            text = str(src.get("text") or "").lower()
            matched = sum(t in text for t in tokens)
            if matched >= max(2, len(tokens)//3): evidence.append({"url": src["url"], "matches": matched, "score": src["score"]})
        results.append({"claim": str(claim)[:600], "status": "supported_by_sources" if evidence else "needs_independent_source",
                        "evidence": sorted(evidence, key=lambda x: (-x["matches"], -x["score"]))[:5]})
    return results
