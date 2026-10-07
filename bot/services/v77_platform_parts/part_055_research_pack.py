from typing import Any
from typing import Iterable

# Auto-split part 55: research_pack
def research_pack(query: str, sources: Iterable[dict[str,Any]]) -> dict[str,Any]:
    ranked=rank_sources(sources,query);claims=[]
    for item in ranked[:8]:
        content=str(item.get("content","") or item.get("snippet","")).strip()
        if content:claims.append(verify_claim(query,[content]))
    return {"query":redact(query,1000),"sources":ranked[:10],"evidence_checks":claims,"confidence":round(sum(x["confidence"] for x in claims)/len(claims),3) if claims else 0}
