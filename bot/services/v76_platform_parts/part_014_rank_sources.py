from typing import Any

# Auto-split part 14: rank_sources
def rank_sources(items: list[dict[str,Any]], query: str="") -> list[dict[str,Any]]:
    seen=set(); out=[]
    for item in items[:100]:
        url=str(item.get("url","")).strip(); title=str(item.get("title","")).strip(); key=hashlib.sha256((url or title).lower().encode()).hexdigest()
        if key in seen: continue
        seen.add(key); score=float(item.get("score",0)); score += 1 if query and any(w in (title+" "+str(item.get("content",""))).lower() for w in query.lower().split()[:5]) else 0
        out.append({**item,"score":round(score,3),"untrusted":True})
    return sorted(out,key=lambda x:x["score"],reverse=True)
