"""v74_platform: knowledge responsibilities."""
from .v74_platform_common import *  # noqa: F401,F403
from . import v74_platform_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


def source_score(url: str, text: str = "", base: float = .4) -> float:
    try: host = (urllib.parse.urlsplit(url).hostname or "").lower()
    except Exception: host = ""
    score = base + (.05 if url.lower().startswith("https://") else 0)
    for domain, weight in _SOURCE_WEIGHTS.items():
        if host.endswith(domain): score = max(score, weight)
    if len(text) > 1500: score += .05
    return round(min(1.0, score), 4)

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

def rag_tokens(text: str) -> list[str]:
    return [t.lower() for t in re.findall(r"[\w\u0600-\u06ff]{3,}", str(text or "")) if t.lower() not in _STOP]

def chunk_document(text: str, *, source: str, chunk_chars: int = 1200, overlap: int = 180) -> list[dict[str, Any]]:
    clean = re.sub(r"\s+", " ", str(text or "")).strip()
    if not clean: return []
    step = max(1, chunk_chars-overlap); chunks=[]
    for i, start in enumerate(range(0, len(clean), step)):
        piece=clean[start:start+chunk_chars]
        if not piece: break
        chunks.append({"source": source, "chunk": i, "text": piece, "tokens": rag_tokens(piece), "chars": len(piece)})
        if start+chunk_chars >= len(clean): break
    return chunks

def rag_rank(query: str, chunks: Iterable[dict[str, Any]], limit: int = 6) -> list[dict[str, Any]]:
    q=Counter(rag_tokens(query)); scored=[]
    for c in chunks:
        toks=Counter(c.get("tokens") or rag_tokens(c.get("text", "")))
        overlap=sum(min(q[t], toks[t]) for t in q)
        if not overlap: continue
        coverage=overlap/max(1,sum(q.values())); density=overlap/max(1,len(toks))
        score=coverage*0.7+density*0.2+min(0.1, len(c.get("text", ""))/12000)
        scored.append((score, coverage, c))
    scored.sort(key=lambda x:(-x[0],-x[1],x[2].get("source", ""),x[2].get("chunk",0)))
    return [{**c, "score": round(s,5), "coverage": round(cov,5)} for s,cov,c in scored[:max(1,min(limit,20))]]

def rag_context(query: str, chunks: Iterable[dict[str, Any]], limit: int = 6, max_chars: int = 9000) -> str:
    blocks=[]; used=0
    for c in rag_rank(query,chunks,limit):
        block=f"[{c['source']}#{c['chunk']} score={c['score']}]\n{sanitize_untrusted_text(c['text'], 2500)}"
        if used+len(block)+2>max_chars: break
        blocks.append(block); used+=len(block)+2
    return "\n\n".join(blocks)
