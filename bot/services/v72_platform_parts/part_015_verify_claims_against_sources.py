from typing import Any

# Auto-split part 15: verify_claims_against_sources
def verify_claims_against_sources(claims: list[str], sources: list[dict[str, Any]]) -> dict[str, Any]:
    """Lexical evidence only; status is never upgraded to proven without evidence."""
    results = []
    for claim in claims[:20]:
        tokens = [x.lower() for x in re.findall(r"[\w\u0600-\u06ff]{4,}", claim)][:10]
        evidence = []
        for src in sources:
            text = (src.get("text") or "").lower()
            matched = sum(1 for t in tokens if t in text)
            if matched >= max(2, len(tokens) // 3): evidence.append({"url": src.get("url"), "matches": matched})
        status = "supported_by_sources" if evidence else "needs_independent_source"
        results.append({"claim": claim[:500], "status": status, "evidence": evidence[:5]})
    return {"ok": bool(results), "claims": results}
