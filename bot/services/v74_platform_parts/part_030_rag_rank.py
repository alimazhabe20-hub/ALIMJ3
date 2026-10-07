from typing import Any
from typing import Iterable

# Auto-split part 30: rag_rank
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
